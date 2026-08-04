# Installation and Requirements

## Checklist

- Python 3.11 or 3.12
- 64-bit Windows 10/11 or supported 64-bit Linux
- Native Tesseract executable if using Tesseract
- English language data (`eng.traineddata`)
- EasyOCR and PyTorch in the project virtual environment
- Internet access for first installation and EasyOCR model download
- Current driver/runtime for the selected GPU backend

## Windows Tesseract

```powershell
winget install --exact --id UB-Mannheim.TesseractOCR
```

Expected path:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Verify:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

## Windows CPU

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_cpu.ps1
.\scripts\start_windows.ps1
```

## Windows NVIDIA

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_nvidia.ps1
.\scripts\start_windows.ps1
```

## Windows AMD

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_amd.ps1
.\scripts\start_windows.ps1
```

The default Windows AMD installation uses CPU PyTorch. Windows ROCm is limited to AMD-listed hardware and current framework combinations.

## Debian/Ubuntu native packages

```bash
sudo apt update
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  tesseract-ocr \
  tesseract-ocr-eng \
  libgl1 \
  libglib2.0-0
```

## Linux CPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_cpu.sh
./scripts/start_linux.sh
```

## Linux NVIDIA

Confirm `nvidia-smi`, then:

```bash
./scripts/install_linux_nvidia.sh
./scripts/start_linux.sh
```

## Linux AMD ROCm

Check AMD's current compatibility matrix, install the matching ROCm release, and choose the corresponding PyTorch wheel:

```bash
export PYTORCH_ROCM_INDEX_URL="https://download.pytorch.org/whl/rocmX.Y"
./scripts/install_linux_amd_rocm.sh
./scripts/start_linux.sh
```

## Diagnostics

```powershell
.\venv\Scripts\python.exe .\scripts\check_accelerator.py
```

or:

```bash
venv/bin/python scripts/check_accelerator.py
```


## Optional AI super-resolution

The main requirements now install `opencv-contrib-python-headless`, which includes OpenCV's `dnn_superres` interface.

Install the optional EDSR x2 model after the normal application setup.

Windows:

```powershell
.\scripts\install_superres_model_windows.ps1
```

Linux:

```bash
./scripts/install_superres_model_linux.sh
```

The model is downloaded from:

```text
https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb
```

and saved to:

```text
models/EDSR_x2.pb
```

See `docs/SUPER_RESOLUTION.md`.
