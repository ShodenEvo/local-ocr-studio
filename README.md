# Local OCR Studio

Local OCR Studio is a privacy-focused web application for enhancing images and recognizing printed, engraved, stamped, or low-contrast text. It combines OpenCV preprocessing, Tesseract OCR, EasyOCR, and optional NVIDIA CUDA or AMD ROCm acceleration.

> Images and OCR results remain on the machine running the application. No database or cloud OCR service is required.

## Features

- Browser-based local interface
- Full-image or rectangular-region OCR
- Tesseract and EasyOCR engines
- Ensemble mode that compares multiple OCR attempts
- OpenCV grayscale, CLAHE, sharpening, threshold, black-hat, and gradient processing
- Text bounding boxes and confidence scores
- Windows and Linux support
- CPU, NVIDIA CUDA, and AMD ROCm modes
- Docker CPU deployment option
- No database

## Accelerator support

| Platform | NVIDIA | AMD | CPU |
|---|---|---|---|
| Windows 10/11 | CUDA supported | CPU supported; DirectML experimental/not yet used by EasyOCR | Supported |
| Linux | CUDA supported | ROCm supported on compatible AMD hardware | Supported |

AMD ROCm support depends on AMD's current hardware/OS compatibility matrix and a matching PyTorch ROCm wheel. On ROCm builds, PyTorch intentionally exposes the GPU through the `torch.cuda` API; the application reports the backend as **ROCm**.

## Quick start

### Windows — NVIDIA GPU

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_nvidia.ps1
.\scripts\start_windows.ps1
```

### Windows — CPU or AMD GPU

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_cpu.ps1
.\scripts\start_windows.ps1
```

Windows AMD acceleration through DirectML is experimental and is not enabled for EasyOCR in the current release.

### Linux — NVIDIA GPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_nvidia.sh
./scripts/start_linux.sh
```

### Linux — AMD ROCm

Install a ROCm version supported by your exact GPU and OS. Obtain the matching PyTorch ROCm wheel index from the official PyTorch selector, then run:

```bash
chmod +x scripts/*.sh
export PYTORCH_ROCM_INDEX_URL="https://download.pytorch.org/whl/rocmX.Y"
./scripts/install_linux_amd_rocm.sh
./scripts/start_linux.sh
```

Replace `rocmX.Y` with the exact index recommended for your installed ROCm version.

### Linux — CPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_cpu.sh
./scripts/start_linux.sh
```

Open `http://127.0.0.1:8095`.

See [Installation](docs/INSTALLATION.md) and [AMD GPU Support](docs/AMD_GPU.md).

## Verify the accelerator

```bash
venv/bin/python scripts/check_accelerator.py
```

```powershell
.\venv\Scripts\python.exe .\scripts\check_accelerator.py
```

Expected AMD Linux output includes `Backend: ROCm` and the Radeon device name.

## Screenshots

Add redacted screenshots under `docs/images/`. Never publish confidential images or real operational identifiers.

## Docker

```bash
docker compose up --build
```

The provided Docker image is CPU-oriented. Native installation is recommended for NVIDIA and AMD GPU acceleration.

## First EasyOCR run

EasyOCR downloads its recognition models the first time it is used. After the model is cached, OCR processing remains local.

## Accuracy guidance

OCR accuracy depends heavily on image acquisition. Use a tight crop, good focus, low-angle illumination for engraving, controlled exposure, and minimal glare. GPU acceleration improves speed, not recognition accuracy by itself.

## Security

The default server binds to localhost. Do not expose it directly to the internet. For network use, add authentication, TLS, request-size limits, and a reverse proxy. See [SECURITY.md](SECURITY.md).

## Roadmap

- PaddleOCR integration
- Batch processing
- User-selectable OCR language packs
- ONNX Runtime backend for broader Windows AMD/Intel acceleration
- Better result voting and format-aware validation
- Reproducible Windows/Linux release packaging

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and use GitHub Issues for bugs and proposals. GPU bug reports must include the output of `scripts/check_accelerator.py`.

## Support the project

After creating your funding profiles, update `.github/FUNDING.yml`. GitHub will display a **Sponsor** button when the funding file is valid.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

## Disclaimer

OCR output can be incorrect. Always verify recognized identifiers against the source image before using them for operational, legal, safety, or compliance decisions.
