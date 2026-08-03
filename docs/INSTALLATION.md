# Installation

## Supported configurations

| OS | Backend | Status |
|---|---|---|
| Windows 10/11 | CPU | Supported |
| Windows 10/11 + NVIDIA | CUDA | Supported |
| Windows 10/11 + AMD | CPU | Supported |
| Windows 10/11 + AMD | DirectML | Experimental; not currently wired into EasyOCR |
| Linux + NVIDIA | CUDA | Supported |
| Linux + compatible AMD | ROCm | Supported |
| Linux | CPU | Supported |

Python 3.11 or 3.12 is recommended.

## Windows CPU or AMD CPU fallback

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_cpu.ps1
.\scripts\start_windows.ps1
```

## Windows NVIDIA CUDA

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_nvidia.ps1
.\scripts\start_windows.ps1
```

## Linux CPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_cpu.sh
./scripts/start_linux.sh
```

## Linux NVIDIA CUDA

Install a compatible NVIDIA driver and confirm `nvidia-smi`:

```bash
chmod +x scripts/*.sh
./scripts/install_linux_nvidia.sh
./scripts/start_linux.sh
```

## Linux AMD ROCm

1. Verify that AMD lists your exact GPU and distribution in its current ROCm compatibility matrix.
2. Install the compatible ROCm release.
3. Use the official PyTorch **Start Locally** selector to obtain the matching ROCm wheel index.
4. Run:

```bash
chmod +x scripts/*.sh
export PYTORCH_ROCM_INDEX_URL="https://download.pytorch.org/whl/rocmX.Y"
./scripts/install_linux_amd_rocm.sh
./scripts/start_linux.sh
```

The installer does not hard-code a ROCm wheel because supported ROCm/PyTorch combinations change over time.

## Verification

```bash
venv/bin/python scripts/check_accelerator.py
```

or on Windows:

```powershell
.\venv\Scripts\python.exe .\scripts\check_accelerator.py
```

Open `http://127.0.0.1:8095`.

EasyOCR downloads model files during first use. Internet is required for that first model download; subsequent OCR processing is local.
