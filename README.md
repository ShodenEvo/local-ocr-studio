# Local OCR Studio

**Make difficult text readable—locally.**

Local OCR Studio is a privacy-focused web application for enhancing images and recognizing printed, engraved, stamped, low-contrast, and real-world text. It combines OpenCV preprocessing, Tesseract OCR, EasyOCR, and optional NVIDIA CUDA or AMD ROCm acceleration.

> Images and OCR results remain on the machine running the application. No database or cloud OCR API is required.

## Features

- Browser-based local interface
- Full-image or rectangular-region OCR
- Tesseract and EasyOCR engines
- Automatic ensemble mode
- Graceful fallback when one OCR engine is missing
- OpenCV grayscale, CLAHE, sharpening, threshold, black-hat, and gradient pipelines
- Text bounding boxes and confidence scores
- Windows and Linux support
- CPU, NVIDIA CUDA, and compatible AMD ROCm modes
- CPU Docker deployment
- No database

## Requirements

Python packages are only part of the installation.

### Required on every platform

- 64-bit operating system
- Python **3.11 or 3.12** recommended
- Git when installing from a clone
- Internet access during initial package installation
- Internet access on the first EasyOCR run to download model files
- At least 4 GB free disk space; GPU installations may need more
- Chrome, Edge, Firefox, or Chromium

### OCR engines

| Engine | Requirement | Optional? |
|---|---|---|
| EasyOCR | Python package plus PyTorch | Yes, if Tesseract is available |
| Tesseract | Native executable plus language data | Yes, if EasyOCR is available |

`pip install pytesseract` installs only the Python wrapper. It does **not** install Tesseract itself.

## Backend support

| Platform | Backend | Status |
|---|---|---|
| Windows 10/11 + CPU | PyTorch CPU | Supported |
| Windows 10/11 + NVIDIA | CUDA | Supported |
| Windows 10/11 + AMD | CPU | Supported and default |
| Windows 11 + selected AMD GPUs | ROCm/PyTorch | Experimental and hardware-dependent |
| Windows + AMD DirectML | DirectML | Not connected to EasyOCR in this release |
| Linux + NVIDIA | CUDA | Supported |
| Linux + compatible AMD | ROCm/HIP | Supported when listed by AMD |
| Linux + CPU | PyTorch CPU | Supported |

GPU acceleration improves speed, not OCR accuracy by itself.

## Windows installation

```powershell
git clone https://github.com/YOUR_USERNAME/local-ocr-studio.git
cd local-ocr-studio
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### NVIDIA

```powershell
.\scripts\install_windows_nvidia.ps1
```

### AMD

```powershell
.\scripts\install_windows_amd.ps1
```

This uses the reliable CPU backend by default. The message:

```text
AMD GPU detected — EasyOCR currently using CPU
```

is expected unless a compatible Windows ROCm/PyTorch environment has been installed and validated.

### CPU-only

```powershell
.\scripts\install_windows_cpu.ps1
```

### Start

```powershell
.\scripts\start_windows.ps1
```

Open `http://127.0.0.1:8095`.

## Windows Tesseract

The Windows install scripts detect Tesseract and can offer to install it through WinGet:

```powershell
winget install --exact --id UB-Mannheim.TesseractOCR
```

Expected executable:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Verify:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

At minimum, `eng` should be listed.

## Linux installation

The included scripts target Debian/Ubuntu-style systems.

### CPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_cpu.sh
./scripts/start_linux.sh
```

### NVIDIA CUDA

Install a compatible driver and verify `nvidia-smi`, then:

```bash
./scripts/install_linux_nvidia.sh
./scripts/start_linux.sh
```

### AMD ROCm

1. Check AMD's current compatibility matrix for the exact GPU, distribution, kernel, and ROCm release.
2. Install the supported ROCm stack.
3. Use PyTorch's current Start Locally selector for the matching ROCm wheel.
4. Run:

```bash
export PYTORCH_ROCM_INDEX_URL="https://download.pytorch.org/whl/rocmX.Y"
./scripts/install_linux_amd_rocm.sh
./scripts/start_linux.sh
```

Replace `rocmX.Y` with the currently supported wheel index.

### Linux Tesseract

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-eng
```

Verify:

```bash
tesseract --version
tesseract --list-langs
```

## Diagnostics

Windows:

```powershell
.\venv\Scripts\python.exe .\scripts\check_accelerator.py
```

Linux:

```bash
venv/bin/python scripts/check_accelerator.py
```

## Status badges

### Tesseract missing

The native executable was not detected. EasyOCR still works. Automatic ensemble mode now skips unavailable Tesseract rather than aborting.

### AMD GPU detected — EasyOCR currently using CPU

AMD hardware exists, but the installed PyTorch build has no active ROCm backend. This is expected for the standard Windows AMD installation.

### CPU mode — no supported GPU backend

PyTorch is installed and OCR works, but CUDA/ROCm acceleration is not active.

## First EasyOCR run

EasyOCR downloads model files on first use. After caching, image processing remains local.

## Restoration and super resolution

The interface includes an optional **Restoration & upscale** stage.

- **Manual controls** apply only the selected deblur, denoise, deblocking, sharpening, and 2×/3×/4× upscale settings.
- **Automatic comparison** tests the original image plus several conservative restored variants and shows every OCR attempt. It does not assume the highest confidence value is correct.
- **Compare original** keeps the original OCR path in the result list so restoration disagreements are visible.
- **Optional AI super-resolution** is disabled unless a compatible OpenCV DNN model is configured. AI-restored pixels are synthetic estimates and must be visually verified.

To enable the optional OpenCV DNN super-resolution backend, first complete the normal application installation, then run:

Windows:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_superres_model_windows.ps1
```

Linux:

```bash
chmod +x scripts/install_superres_model_linux.sh
./scripts/install_superres_model_linux.sh
```

The installer downloads:

```text
https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb
```

to the portable project path:

```text
models/EDSR_x2.pb
```

The application detects this path automatically. See [AI super-resolution setup](docs/SUPER_RESOLUTION.md) for manual installation, custom paths, verification, licensing, and troubleshooting.

The model file is not committed to this repository. Manual and automatic OCR-safe restoration continue to work without it.

**Important:** Super resolution cannot recover information that is absent from the source. Generative or learned restoration can create plausible but incorrect character strokes. Always compare against the original.

## Docker

```bash
docker compose up --build
```

The provided Docker image is CPU-oriented.

## Accuracy guidance

Use a tight crop, good focus, sufficient resolution, controlled exposure, low-angle lighting for engraving, and minimal glare. Use `Single line` for one identifier and `Sparse text` for text distributed around an image.

## Documentation

- [Detailed installation](docs/INSTALLATION.md)
- [AMD GPU support](docs/AMD_GPU.md)
- [AI super-resolution setup](docs/SUPER_RESOLUTION.md)
- [Windows service and control panel](docs/WINDOWS_SERVICE.md)
- [Privacy](docs/PRIVACY.md)
- [Security](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).

## Disclaimer

OCR output can be incorrect. Always verify recognized identifiers against the source image before operational, legal, safety, or compliance use.


## Consensus-based automatic result selection

Reported OCR confidence is not treated as proof of correctness. The default selector now prioritizes agreement across engines, original/restored sources, and enhancement paths.

New controls:

- Expected minimum text length
- Expected maximum text length
- Optional requirement for both letters and numbers
- Consensus selection
- Prefer-original selection
- Highest-confidence diagnostic selection
- Clickable manual choice from all recognition attempts

For shallow engraved identifiers, start with `Single line`, set the expected identifier length, and use grayscale, CLAHE, CLAHE + sharpen, or Engraving relief before hard threshold methods.


## Windows background service and control panel

Build the Windows executables after completing the normal installation:

```powershell
.\scripts\build_windows_executables.ps1
.\scripts\install_windows_service.ps1
```

This creates an automatically started Windows service and a tray control panel. See [Windows service and control panel](docs/WINDOWS_SERVICE.md).
