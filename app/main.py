from __future__ import annotations

import base64
import io
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import cv2
import numpy as np
import pytesseract
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from starlette.requests import Request

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

app = FastAPI(title="Local OCR Studio", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Configure Tesseract. This remains local and does not upload data anywhere.
TESSERACT_CANDIDATES = [
    os.getenv("TESSERACT_CMD"),
    shutil.which("tesseract"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for candidate in TESSERACT_CANDIDATES:
    if candidate and Path(candidate).exists():
        pytesseract.pytesseract.tesseract_cmd = str(candidate)
        break

_easyocr_reader = None
_easyocr_device = None
_easyocr_lock = Lock()


def get_torch_status() -> dict[str, Any]:
    """Return PyTorch/CUDA status without making GPU support mandatory."""
    try:
        import torch
        cuda_available = bool(torch.cuda.is_available())
        return {
            "installed": True,
            "version": str(torch.__version__),
            "cuda_available": cuda_available,
            "cuda_runtime": str(torch.version.cuda) if torch.version.cuda else None,
            "device_count": int(torch.cuda.device_count()) if cuda_available else 0,
            "device_name": torch.cuda.get_device_name(0) if cuda_available else None,
        }
    except Exception as exc:
        return {
            "installed": False,
            "version": None,
            "cuda_available": False,
            "cuda_runtime": None,
            "device_count": 0,
            "device_name": None,
            "error": str(exc),
        }


@dataclass
class OCRHit:
    text: str
    confidence: float
    box: list[list[int]]
    engine: str
    method: str


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/api/status")
def status() -> dict[str, Any]:
    tesseract_ok = False
    tesseract_version = None
    try:
        tesseract_version = str(pytesseract.get_tesseract_version())
        tesseract_ok = True
    except Exception:
        pass

    easyocr_installed = False
    try:
        import easyocr  # noqa: F401
        easyocr_installed = True
    except Exception:
        pass

    torch_status = get_torch_status()
    return {
        "tesseract": {"available": tesseract_ok, "version": tesseract_version},
        "easyocr": {
            "available": easyocr_installed,
            "loaded": _easyocr_reader is not None,
            "device": _easyocr_device,
        },
        "gpu": torch_status,
    }


@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    engine: str = Form("ensemble"),
    method: str = Form("auto"),
    psm: int = Form(11),
    upscale: float = Form(3.0),
    clahe: float = Form(2.5),
    sharpen: float = Form(0.7),
    blur: int = Form(1),
    confidence: float = Form(0.0),
    invert: bool = Form(False),
    allowlist: str = Form(""),
    crop_x: int = Form(0),
    crop_y: int = Form(0),
    crop_w: int = Form(0),
    crop_h: int = Form(0),
) -> dict[str, Any]:
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty upload")

    image = decode_image(raw)
    if image is None:
        raise HTTPException(400, "Unsupported or invalid image")

    source = crop_image(image, crop_x, crop_y, crop_w, crop_h)
    candidates = enhancement_candidates(source, upscale, clahe, sharpen, blur)

    if invert:
        candidates = {name: cv2.bitwise_not(img) for name, img in candidates.items()}

    selected_names = list(candidates) if method == "auto" else [method]
    selected_names = [name for name in selected_names if name in candidates]
    if not selected_names:
        selected_names = ["clahe_sharpen"]

    engines = [engine] if engine != "ensemble" else ["tesseract", "easyocr"]
    all_hits: list[OCRHit] = []
    attempts: list[dict[str, Any]] = []

    for method_name in selected_names:
        candidate = candidates[method_name]
        if "tesseract" in engines:
            hits = run_tesseract(candidate, method_name, psm, confidence, allowlist)
            all_hits.extend(hits)
            attempts.append(summarize_attempt("tesseract", method_name, hits))

        if "easyocr" in engines:
            try:
                hits = run_easyocr(candidate, method_name, confidence, allowlist)
                all_hits.extend(hits)
                attempts.append(summarize_attempt("easyocr", method_name, hits))
            except ImportError:
                attempts.append({
                    "engine": "easyocr",
                    "method": method_name,
                    "error": "EasyOCR is not installed",
                    "text": "",
                    "confidence": 0,
                })

    best_attempt = choose_best_attempt(attempts)
    best_method = best_attempt.get("method", selected_names[0])
    best_engine = best_attempt.get("engine", engine)
    best_image = candidates.get(best_method, candidates[selected_names[0]])

    best_hits = [
        hit for hit in all_hits
        if hit.method == best_method and hit.engine == best_engine
    ]
    annotated = draw_hits(best_image, best_hits)

    return {
        "text": best_attempt.get("text", ""),
        "confidence": round(float(best_attempt.get("confidence", 0.0)), 2),
        "engine": best_engine,
        "method": best_method,
        "hits": [hit_to_dict(hit) for hit in best_hits],
        "attempts": sorted(attempts, key=lambda x: x.get("score", -9999), reverse=True),
        "source_image": encode_png(source),
        "enhanced_image": encode_png(best_image),
        "annotated_image": encode_png(annotated),
    }


def decode_image(raw: bytes) -> np.ndarray | None:
    array = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def crop_image(image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    if w <= 0 or h <= 0:
        return image.copy()
    height, width = image.shape[:2]
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width - x))
    h = max(1, min(h, height - y))
    return image[y:y + h, x:x + w].copy()


def enhancement_candidates(
    image: np.ndarray,
    upscale: float,
    clahe_limit: float,
    sharpen_strength: float,
    blur_size: int,
) -> dict[str, np.ndarray]:
    upscale = max(1.0, min(float(upscale), 6.0))
    enlarged = cv2.resize(image, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)

    blur_size = int(blur_size)
    if blur_size > 1:
        blur_size += 1 if blur_size % 2 == 0 else 0
        gray = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)

    denoised = cv2.bilateralFilter(gray, 5, 35, 35)
    clahe_img = cv2.createCLAHE(
        clipLimit=max(1.0, float(clahe_limit)), tileGridSize=(8, 8)
    ).apply(denoised)

    soft = cv2.GaussianBlur(clahe_img, (0, 0), 1.2)
    sharpened = cv2.addWeighted(
        clahe_img, 1.0 + max(0.0, sharpen_strength),
        soft, -max(0.0, sharpen_strength), 0
    )

    _, otsu = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 7
    )
    adaptive_inv = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 31, 7
    )

    # Engraving-oriented black-hat and gradient variants.
    bh_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
    blackhat = cv2.morphologyEx(clahe_img, cv2.MORPH_BLACKHAT, bh_kernel)
    blackhat = cv2.normalize(blackhat, None, 0, 255, cv2.NORM_MINMAX)
    _, blackhat_bin = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    grad_x = cv2.Sobel(clahe_img, cv2.CV_32F, 1, 0, ksize=3)
    gradient = cv2.convertScaleAbs(grad_x)
    gradient = cv2.morphologyEx(
        gradient, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3)), iterations=1
    )

    return {
        "grayscale": add_border(gray),
        "clahe": add_border(clahe_img),
        "clahe_sharpen": add_border(sharpened),
        "otsu": add_border(otsu),
        "adaptive": add_border(adaptive),
        "adaptive_inverted": add_border(adaptive_inv),
        "blackhat": add_border(blackhat_bin),
        "horizontal_gradient": add_border(gradient),
    }


def add_border(image: np.ndarray, size: int = 30) -> np.ndarray:
    # Tesseract often benefits from a border around tightly cropped text.
    median = int(np.median(image))
    value = 255 if median > 100 else 0
    return cv2.copyMakeBorder(image, size, size, size, size, cv2.BORDER_CONSTANT, value=value)


def run_tesseract(
    image: np.ndarray,
    method: str,
    psm: int,
    minimum_confidence: float,
    allowlist: str,
) -> list[OCRHit]:
    config = f"--oem 3 --psm {int(psm)} -c preserve_interword_spaces=1"
    if allowlist.strip():
        safe = re.sub(r"\s+", "", allowlist)
        config += f" -c tessedit_char_whitelist={safe}"

    try:
        data = pytesseract.image_to_data(
            image, lang="eng", config=config,
            output_type=pytesseract.Output.DICT
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise HTTPException(500, "Tesseract is not installed or configured") from exc

    hits: list[OCRHit] = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1
        if not text or conf < minimum_confidence:
            continue
        x, y = int(data["left"][i]), int(data["top"][i])
        w, h = int(data["width"][i]), int(data["height"][i])
        hits.append(OCRHit(text, conf / 100.0, [[x, y], [x+w, y], [x+w, y+h], [x, y+h]], "tesseract", method))
    return hits


def get_easyocr_reader():
    global _easyocr_reader, _easyocr_device
    with _easyocr_lock:
        if _easyocr_reader is None:
            try:
                import easyocr
                import torch
            except ImportError as exc:
                raise ImportError("EasyOCR/PyTorch is not installed") from exc

            # EasyOCR uses CUDA automatically when the installed PyTorch build
            # can see an NVIDIA GPU. Otherwise it falls back safely to CPU.
            use_cuda = bool(torch.cuda.is_available())
            _easyocr_device = "cuda" if use_cuda else "cpu"
            _easyocr_reader = easyocr.Reader(
                ["en"],
                gpu="cuda" if use_cuda else False,
                verbose=True,
            )
    return _easyocr_reader


def run_easyocr(
    image: np.ndarray,
    method: str,
    minimum_confidence: float,
    allowlist: str,
) -> list[OCRHit]:
    reader = get_easyocr_reader()
    kwargs: dict[str, Any] = {
        "detail": 1,
        "paragraph": False,
        "decoder": "beamsearch",
        "beamWidth": 10,
        "text_threshold": 0.25,
        "low_text": 0.15,
        "link_threshold": 0.2,
        "mag_ratio": 1.5,
    }
    if allowlist.strip():
        kwargs["allowlist"] = allowlist

    results = reader.readtext(image, **kwargs)
    hits: list[OCRHit] = []
    for box, text, conf in results:
        if not text.strip() or float(conf) < minimum_confidence / 100.0:
            continue
        points = [[int(p[0]), int(p[1])] for p in box]
        hits.append(OCRHit(text.strip(), float(conf), points, "easyocr", method))
    return hits


def summarize_attempt(engine: str, method: str, hits: list[OCRHit]) -> dict[str, Any]:
    ordered = sorted(hits, key=lambda h: (min(p[1] for p in h.box), min(p[0] for p in h.box)))
    text = " ".join(hit.text for hit in ordered).strip()
    confidence = float(np.mean([hit.confidence for hit in hits])) if hits else 0.0
    alnum = sum(ch.isalnum() for ch in text)
    mixed = any(ch.isalpha() for ch in text) and any(ch.isdigit() for ch in text)
    score = confidence * 100 + min(alnum, 80) * 0.5 + (12 if mixed else 0)
    if not text:
        score = -1000
    return {
        "engine": engine,
        "method": method,
        "text": text,
        "confidence": confidence * 100,
        "score": score,
        "count": len(hits),
    }


def choose_best_attempt(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [a for a in attempts if a.get("text")]
    if not valid:
        return {"text": "", "confidence": 0, "engine": "none", "method": "none", "score": -1000}
    return max(valid, key=lambda a: a.get("score", -1000))


def draw_hits(image: np.ndarray, hits: list[OCRHit]) -> np.ndarray:
    canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()
    for hit in hits:
        pts = np.array(hit.box, dtype=np.int32)
        cv2.polylines(canvas, [pts], True, (0, 255, 0), 2)
        x, y = int(pts[:, 0].min()), int(pts[:, 1].min())
        label = f"{hit.text} {hit.confidence * 100:.0f}%"
        cv2.putText(canvas, label, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
    return canvas


def hit_to_dict(hit: OCRHit) -> dict[str, Any]:
    return {
        "text": hit.text,
        "confidence": round(hit.confidence * 100, 2),
        "box": hit.box,
        "engine": hit.engine,
        "method": hit.method,
    }


def encode_png(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Could not encode image")
    return "data:image/png;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
