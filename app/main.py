from __future__ import annotations

import base64
import io
import os
import platform
import re
import shutil
import subprocess
import tempfile
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
PROJECT_DIR = BASE_DIR.parent
DEFAULT_SUPERRES_MODEL_PATH = PROJECT_DIR / "models" / "EDSR_x2.pb"

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


def detect_display_adapters() -> list[str]:
    """Best-effort hardware detection used only for clearer status messages."""
    adapters: list[str] = []

    try:
        if platform.system() == "Windows":
            command = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | "
                "Select-Object -ExpandProperty Name",
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            adapters = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
            ]
        elif platform.system() == "Linux":
            result = subprocess.run(
                ["sh", "-c", "lspci 2>/dev/null | grep -Ei 'VGA|3D|Display'"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            adapters = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
            ]
    except Exception:
        pass

    return adapters


def get_torch_status() -> dict[str, Any]:
    """Report both installed hardware and the active PyTorch accelerator."""
    adapters = detect_display_adapters()
    adapter_text = " | ".join(adapters).lower()
    amd_detected = any(token in adapter_text for token in ("amd", "radeon"))
    nvidia_detected = "nvidia" in adapter_text

    try:
        import torch

        gpu_available = bool(torch.cuda.is_available())
        hip_runtime = (
            str(torch.version.hip)
            if getattr(torch.version, "hip", None)
            else None
        )
        cuda_runtime = str(torch.version.cuda) if torch.version.cuda else None

        if gpu_available and hip_runtime:
            backend = "rocm"
        elif gpu_available and cuda_runtime:
            backend = "cuda"
        else:
            backend = "cpu"

        note = None
        if backend == "cpu" and amd_detected and platform.system() == "Windows":
            note = (
                "AMD GPU detected, but this PyTorch environment has no active "
                "ROCm backend. EasyOCR is running on CPU."
            )
        elif backend == "cpu" and amd_detected:
            note = (
                "AMD GPU detected, but a compatible ROCm-enabled PyTorch build "
                "is not active."
            )
        elif backend == "cpu" and nvidia_detected:
            note = (
                "NVIDIA GPU detected, but the installed PyTorch build is CPU-only."
            )

        return {
            "installed": True,
            "version": str(torch.__version__),
            "backend": backend,
            "cuda_available": gpu_available,
            "gpu_available": gpu_available,
            "cuda_runtime": cuda_runtime,
            "hip_runtime": hip_runtime,
            "device_count": int(torch.cuda.device_count()) if gpu_available else 0,
            "device_name": torch.cuda.get_device_name(0) if gpu_available else None,
            "display_adapters": adapters,
            "amd_hardware_detected": amd_detected,
            "nvidia_hardware_detected": nvidia_detected,
            "note": note,
        }
    except Exception as exc:
        return {
            "installed": False,
            "version": None,
            "backend": "unavailable",
            "cuda_available": False,
            "gpu_available": False,
            "cuda_runtime": None,
            "hip_runtime": None,
            "device_count": 0,
            "device_name": None,
            "display_adapters": adapters,
            "amd_hardware_detected": amd_detected,
            "nvidia_hardware_detected": nvidia_detected,
            "note": "PyTorch is not installed.",
            "error": str(exc),
        }


def tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def easyocr_available() -> bool:
    try:
        import easyocr  # noqa: F401
        return True
    except Exception:
        return False


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
    tesseract_ok = tesseract_available()
    tesseract_version = None
    if tesseract_ok:
        tesseract_version = str(pytesseract.get_tesseract_version())

    easyocr_installed = easyocr_available()

    torch_status = get_torch_status()
    return {
        "tesseract": {"available": tesseract_ok, "version": tesseract_version},
        "easyocr": {
            "available": easyocr_installed,
            "loaded": _easyocr_reader is not None,
            "device": _easyocr_device,
        },
        "gpu": torch_status,
        "restoration": get_restoration_status(),
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
    restoration_enabled: bool = Form(False),
    restoration_mode: str = Form("manual"),
    restoration_scale: int = Form(2),
    deblur_strength: float = Form(0.8),
    denoise_strength: int = Form(6),
    deblock_strength: int = Form(1),
    restoration_sharpen: float = Form(0.5),
    compare_original: bool = Form(True),
    ai_super_resolution: bool = Form(False),
    expected_min_length: int = Form(4),
    expected_max_length: int = Form(24),
    require_mixed_alnum: bool = Form(False),
    selection_strategy: str = Form("consensus"),
) -> dict[str, Any]:
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty upload")

    image = decode_image(raw)
    if image is None:
        raise HTTPException(400, "Unsupported or invalid image")

    source = crop_image(image, crop_x, crop_y, crop_w, crop_h)

    image_sources: dict[str, np.ndarray] = {"original": source}
    restoration_notes: list[str] = []

    if restoration_enabled:
        if restoration_mode == "automatic":
            image_sources.update(
                automatic_restoration_variants(
                    source,
                    scale=restoration_scale,
                    include_ai=ai_super_resolution,
                )
            )
            restoration_notes.append(
                "Automatic restoration tested multiple restoration paths. "
                "Review disagreements manually; confidence alone is not authoritative."
            )
        else:
            restored = restore_image_manual(
                source,
                scale=restoration_scale,
                deblur_strength=deblur_strength,
                denoise_strength=denoise_strength,
                deblock_strength=deblock_strength,
                sharpen_strength=restoration_sharpen,
            )
            image_sources["restored_manual"] = restored

            if ai_super_resolution:
                ai_image, ai_note = run_optional_ai_super_resolution(
                    source, restoration_scale
                )
                if ai_image is not None:
                    image_sources["restored_ai"] = ai_image
                if ai_note:
                    restoration_notes.append(ai_note)

        if not compare_original:
            image_sources.pop("original", None)

    candidates: dict[str, np.ndarray] = {}
    candidate_sources: dict[str, str] = {}

    for source_name, source_image in image_sources.items():
        source_candidates = enhancement_candidates(
            source_image, upscale, clahe, sharpen, blur
        )
        for enhancement_name, candidate in source_candidates.items():
            combined_name = f"{source_name}::{enhancement_name}"
            candidates[combined_name] = (
                cv2.bitwise_not(candidate) if invert else candidate
            )
            candidate_sources[combined_name] = source_name

    if method == "auto":
        selected_names = list(candidates)
    else:
        selected_names = [
            name for name in candidates
            if name.endswith(f"::{method}")
        ]

    if not selected_names:
        selected_names = [next(iter(candidates))]

    requested_engines = (
        [engine] if engine != "ensemble" else ["tesseract", "easyocr"]
    )
    engines: list[str] = []

    if "tesseract" in requested_engines and tesseract_available():
        engines.append("tesseract")
    if "easyocr" in requested_engines and easyocr_available():
        engines.append("easyocr")

    if not engines:
        raise HTTPException(
            500,
            "No OCR engine is available. Install Tesseract and/or EasyOCR.",
        )

    all_hits: list[OCRHit] = []
    attempts: list[dict[str, Any]] = []

    if "tesseract" in requested_engines and "tesseract" not in engines:
        attempts.append({
            "engine": "tesseract",
            "method": "unavailable",
            "text": "",
            "confidence": 0,
            "score": -1000,
            "count": 0,
            "error": "Tesseract is not installed or was not detected.",
        })

    if "easyocr" in requested_engines and "easyocr" not in engines:
        attempts.append({
            "engine": "easyocr",
            "method": "unavailable",
            "text": "",
            "confidence": 0,
            "score": -1000,
            "count": 0,
            "error": "EasyOCR is not installed.",
        })

    for method_name in selected_names:
        candidate = candidates[method_name]

        if "tesseract" in engines:
            hits = run_tesseract(
                candidate, method_name, psm, confidence, allowlist
            )
            all_hits.extend(hits)
            attempts.append(
                summarize_attempt("tesseract", method_name, hits)
            )

        if "easyocr" in engines:
            hits = run_easyocr(
                candidate, method_name, confidence, allowlist
            )
            all_hits.extend(hits)
            attempts.append(
                summarize_attempt("easyocr", method_name, hits)
            )

    attempts = enrich_attempts_with_consensus(
        attempts,
        expected_min_length=expected_min_length,
        expected_max_length=expected_max_length,
        require_mixed_alnum=require_mixed_alnum,
    )
    best_attempt = choose_best_attempt(
        attempts,
        strategy=selection_strategy,
    )
    best_method = best_attempt.get("method", selected_names[0])
    best_engine = best_attempt.get("engine", engine)
    best_image = candidates.get(best_method, candidates[selected_names[0]])
    best_source = candidate_sources.get(best_method, "original")
    display_method = best_method.split("::", 1)[-1]

    best_hits = [
        hit for hit in all_hits
        if hit.method == best_method and hit.engine == best_engine
    ]
    annotated = draw_hits(best_image, best_hits)

    return {
        "text": best_attempt.get("text", ""),
        "confidence": round(float(best_attempt.get("confidence", 0.0)), 2),
        "engine": best_engine,
        "method": display_method,
        "processing_source": best_source,
        "restoration_enabled": restoration_enabled,
        "restoration_mode": restoration_mode if restoration_enabled else "off",
        "restoration_notes": restoration_notes,
        "selection_strategy": selection_strategy,
        "expected_min_length": expected_min_length,
        "expected_max_length": expected_max_length,
        "require_mixed_alnum": require_mixed_alnum,
        "hits": [hit_to_dict(hit) for hit in best_hits],
        "attempts": sorted(attempts, key=lambda x: x.get("score", -9999), reverse=True),
        "source_image": encode_png(source),
        "enhanced_image": encode_png(best_image),
        "restored_image": encode_png(
            image_sources.get(best_source, source)
        ),
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




def get_superres_model_path() -> Path | None:
    configured = os.getenv("SUPERRES_MODEL_PATH", "").strip()

    if configured:
        return Path(configured).expanduser()

    if DEFAULT_SUPERRES_MODEL_PATH.exists():
        return DEFAULT_SUPERRES_MODEL_PATH

    return None


def get_restoration_status() -> dict[str, Any]:
    model_path = get_superres_model_path()
    model_exists = bool(model_path and model_path.exists())
    dnn_superres_available = hasattr(cv2, "dnn_superres")

    return {
        "manual_available": True,
        "automatic_available": True,
        "ai_available": bool(model_exists and dnn_superres_available),
        "ai_model_path": str(model_path) if model_exists else None,
        "ai_note": (
            "Optional OpenCV DNN super-resolution model is ready."
            if model_exists and dnn_superres_available
            else "AI super-resolution is optional. Run the model installer or "
                 "place EDSR_x2.pb under the project models directory."
        ),
    }


def odd_kernel(value: int, minimum: int = 1, maximum: int = 15) -> int:
    value = max(minimum, min(int(value), maximum))
    return value if value % 2 else value + 1


def reduce_block_artifacts(image: np.ndarray, strength: int) -> np.ndarray:
    if strength <= 0:
        return image.copy()

    # Edge-preserving deblocking. Multiple light passes are safer for OCR than
    # one aggressive pass that can erase thin character strokes.
    result = image.copy()
    passes = max(1, min(int(strength), 3))
    for _ in range(passes):
        result = cv2.bilateralFilter(result, 5, 28, 28)
    return result


def wiener_like_deblur(gray: np.ndarray, strength: float) -> np.ndarray:
    """Conservative frequency-domain deblur intended for OCR preprocessing."""
    strength = max(0.0, min(float(strength), 2.0))
    if strength <= 0:
        return gray.copy()

    sigma = 0.8 + strength * 0.9
    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma)
    amount = 0.45 + strength * 0.55
    return cv2.addWeighted(gray, 1.0 + amount, blurred, -amount, 0)


def restore_image_manual(
    image: np.ndarray,
    scale: int,
    deblur_strength: float,
    denoise_strength: int,
    deblock_strength: int,
    sharpen_strength: float,
) -> np.ndarray:
    scale = max(1, min(int(scale), 4))
    working = reduce_block_artifacts(image, deblock_strength)

    if denoise_strength > 0:
        h = max(1, min(int(denoise_strength), 20))
        working = cv2.fastNlMeansDenoisingColored(
            working, None, h, h, 7, 21
        )

    if scale > 1:
        working = cv2.resize(
            working,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LANCZOS4,
        )

    lab = cv2.cvtColor(working, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    lightness = wiener_like_deblur(lightness, deblur_strength)

    if sharpen_strength > 0:
        soft = cv2.GaussianBlur(lightness, (0, 0), 1.0)
        amount = max(0.0, min(float(sharpen_strength), 2.5))
        lightness = cv2.addWeighted(
            lightness, 1.0 + amount, soft, -amount, 0
        )

    restored = cv2.cvtColor(
        cv2.merge((lightness, a_channel, b_channel)),
        cv2.COLOR_LAB2BGR,
    )
    return restored


def automatic_restoration_variants(
    image: np.ndarray,
    scale: int,
    include_ai: bool,
) -> dict[str, np.ndarray]:
    scale = max(2, min(int(scale), 4))
    variants = {
        "restored_light": restore_image_manual(image, scale, 0.35, 3, 0, 0.25),
        "restored_balanced": restore_image_manual(image, scale, 0.8, 6, 1, 0.55),
        "restored_strong": restore_image_manual(image, scale, 1.35, 9, 2, 0.9),
    }

    # Keep a pure resampling path because aggressive restoration can damage
    # already-readable character edges.
    variants["upscaled_lanczos"] = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_LANCZOS4,
    )

    if include_ai:
        ai_image, _ = run_optional_ai_super_resolution(image, scale)
        if ai_image is not None:
            variants["restored_ai"] = ai_image

    return variants


def run_optional_ai_super_resolution(
    image: np.ndarray,
    requested_scale: int,
) -> tuple[np.ndarray | None, str | None]:
    model_path = get_superres_model_path()
    if model_path is None:
        return None, (
            "AI super-resolution model is not installed. Run the model installer "
            "or place EDSR_x2.pb under the project models directory. Manual and "
            "automatic OCR-safe restoration were still applied."
        )

    if not model_path.exists():
        return None, f"AI model was not found: {model_path}"

    if not hasattr(cv2, "dnn_superres"):
        return None, (
            "AI super-resolution requires opencv-contrib-python. "
            "The standard opencv-python package does not include dnn_superres."
        )

    scale = max(2, min(int(requested_scale), 4))
    model_name = os.getenv("SUPERRES_MODEL_NAME", "edsr").strip().lower()
    model_scale = int(os.getenv("SUPERRES_MODEL_SCALE", str(scale)))

    try:
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(model_path))
        sr.setModel(model_name, model_scale)
        output = sr.upsample(image)
        return output, (
            "AI-restored pixels are synthetic estimates. Verify every character "
            "against the original image."
        )
    except Exception as exc:
        return None, f"AI super-resolution failed: {exc}"


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

    light_blur = cv2.GaussianBlur(clahe_img, (0, 0), 1.0)
    relief_x = cv2.Scharr(light_blur, cv2.CV_32F, 1, 0)
    relief_y = cv2.Scharr(light_blur, cv2.CV_32F, 0, 1)
    relief_mag = cv2.magnitude(relief_x, relief_y)
    relief_mag = cv2.normalize(
        relief_mag, None, 0, 255, cv2.NORM_MINMAX
    ).astype(np.uint8)
    relief_soft = cv2.GaussianBlur(relief_mag, (3, 3), 0)
    relief = cv2.addWeighted(
        clahe_img, 0.72, relief_soft, 0.28, 0
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
        "engraving_relief": add_border(relief),
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

            # PyTorch exposes NVIDIA CUDA and AMD ROCm devices through
            # torch.cuda, so EasyOCR uses the same GPU path for either backend.
            use_gpu = bool(torch.cuda.is_available())
            if use_gpu and getattr(torch.version, "hip", None):
                _easyocr_device = "rocm"
            elif use_gpu:
                _easyocr_device = "cuda"
            else:
                _easyocr_device = "cpu"

            _easyocr_reader = easyocr.Reader(
                ["en"],
                gpu=True if use_gpu else False,
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


def normalize_ocr_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            current.append(min(
                current[j - 1] + 1,
                previous[j] + 1,
                previous[j - 1] + (left_char != right_char),
            ))
        previous = current
    return previous[-1]


def method_risk_penalty(method: str) -> float:
    name = method.lower()
    penalty = 0.0

    if "adaptive_inverted" in name:
        penalty += 26.0
    elif "adaptive" in name:
        penalty += 17.0
    elif "otsu" in name:
        penalty += 13.0
    elif "blackhat" in name:
        penalty += 11.0
    elif "horizontal_gradient" in name:
        penalty += 8.0

    if "restored_strong" in name:
        penalty += 18.0
    elif "restored_balanced" in name:
        penalty += 7.0
    elif "restored_ai" in name:
        penalty += 9.0
    elif "restored_light" in name:
        penalty += 2.0

    if method.startswith("original::"):
        penalty -= 5.0

    return penalty


def summarize_attempt(
    engine: str,
    method: str,
    hits: list[OCRHit],
) -> dict[str, Any]:
    ordered = sorted(
        hits,
        key=lambda hit: (
            min(point[1] for point in hit.box),
            min(point[0] for point in hit.box),
        ),
    )
    text = " ".join(hit.text for hit in ordered).strip()
    normalized = normalize_ocr_text(text)
    confidence = (
        float(np.mean([hit.confidence for hit in hits]))
        if hits else 0.0
    )

    return {
        "engine": engine,
        "method": method,
        "text": text,
        "normalized_text": normalized,
        "confidence": confidence * 100,
        "count": len(hits),
        "consensus_count": 0,
        "consensus_engines": 0,
        "consensus_sources": 0,
        "score": -1000 if not text else 0,
    }


def enrich_attempts_with_consensus(
    attempts: list[dict[str, Any]],
    expected_min_length: int,
    expected_max_length: int,
    require_mixed_alnum: bool,
) -> list[dict[str, Any]]:
    minimum = max(1, int(expected_min_length))
    maximum = max(minimum, int(expected_max_length))
    valid = [
        attempt for attempt in attempts
        if attempt.get("normalized_text")
    ]

    for attempt in attempts:
        normalized = attempt.get("normalized_text", "")
        if not normalized:
            attempt["score"] = -1000
            attempt["warnings"] = ["no text"]
            continue

        length = len(normalized)
        has_letters = any(char.isalpha() for char in normalized)
        has_digits = any(char.isdigit() for char in normalized)
        mixed = has_letters and has_digits

        max_distance = 0 if length <= 4 else 1
        if length >= 10:
            max_distance = 2

        close_attempts = []
        for other in valid:
            other_text = other.get("normalized_text", "")
            if abs(len(other_text) - length) > max_distance:
                continue
            if levenshtein_distance(normalized, other_text) <= max_distance:
                close_attempts.append(other)

        engines = {
            item.get("engine") for item in close_attempts
            if item.get("engine")
        }
        sources = {
            str(item.get("method", "")).split("::", 1)[0]
            for item in close_attempts
        }

        attempt["consensus_count"] = len(close_attempts)
        attempt["consensus_engines"] = len(engines)
        attempt["consensus_sources"] = len(sources)

        score = float(attempt.get("confidence", 0.0)) * 0.28
        score += min(len(close_attempts), 8) * 13.0
        score += max(0, len(engines) - 1) * 18.0
        score += max(0, len(sources) - 1) * 10.0

        if minimum <= length <= maximum:
            score += 28.0
        else:
            distance = (
                minimum - length
                if length < minimum else length - maximum
            )
            score -= 35.0 + distance * 8.0

        if length <= 2:
            score -= 70.0
        elif length == 3:
            score -= 38.0

        if mixed:
            score += 12.0
        elif require_mixed_alnum:
            score -= 55.0

        score -= method_risk_penalty(
            str(attempt.get("method", ""))
        )

        detection_count = int(attempt.get("count", 0))
        if detection_count > max(4, length):
            score -= min(
                25.0,
                (detection_count - length) * 2.0,
            )

        attempt["score"] = score
        attempt["within_expected_length"] = minimum <= length <= maximum
        attempt["mixed_alnum"] = mixed

        warnings = []
        if length < minimum:
            warnings.append(f"too short ({length} < {minimum})")
        if length > maximum:
            warnings.append(f"too long ({length} > {maximum})")
        if require_mixed_alnum and not mixed:
            warnings.append("letters and numbers required")
        if len(close_attempts) <= 1:
            warnings.append("no consensus")
        attempt["warnings"] = warnings

    return attempts


def choose_best_attempt(
    attempts: list[dict[str, Any]],
    strategy: str = "consensus",
) -> dict[str, Any]:
    valid = [attempt for attempt in attempts if attempt.get("text")]
    if not valid:
        return {
            "text": "",
            "confidence": 0,
            "engine": "none",
            "method": "none",
            "score": -1000,
        }

    if strategy == "confidence":
        return max(
            valid,
            key=lambda attempt: float(
                attempt.get("confidence", 0.0)
            ),
        )

    if strategy == "original_first":
        original = [
            attempt for attempt in valid
            if str(attempt.get("method", "")).startswith("original::")
        ]
        if original:
            return max(
                original,
                key=lambda attempt: attempt.get("score", -1000),
            )

    return max(
        valid,
        key=lambda attempt: attempt.get("score", -1000),
    )


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
