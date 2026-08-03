# Local OCR Studio

Local OCR Studio is a privacy-focused web application for enhancing images and recognizing printed, engraved, stamped, or low-contrast text. It combines OpenCV preprocessing, Tesseract OCR, EasyOCR, and optional NVIDIA CUDA acceleration.

> Images and OCR results remain on the machine running the application. No database or cloud OCR service is required.

## Features

- Browser-based local interface
- Full-image or rectangular-region OCR
- Tesseract and EasyOCR engines
- Ensemble mode that compares multiple OCR attempts
- OpenCV grayscale, CLAHE, sharpening, threshold, black-hat, and gradient processing
- Text bounding boxes and confidence scores
- Windows and Linux support
- CPU mode and optional NVIDIA GPU acceleration
- Docker deployment option
- No database

## Screenshots

Add screenshots under `docs/images/`, then replace this section with:

```markdown
![Local OCR Studio interface](docs/images/interface.png)
```

Redact confidential serial numbers and private images before committing screenshots.

## Quick start

### Windows with NVIDIA GPU

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_nvidia.ps1
.\scripts\start_windows.ps1
```

### Windows CPU

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_cpu.ps1
.\scripts\start_windows.ps1
```

### Linux with NVIDIA GPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_nvidia.sh
./scripts/start_linux.sh
```

### Linux CPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_cpu.sh
./scripts/start_linux.sh
```

Open `http://127.0.0.1:8095`.

See [Installation](docs/INSTALLATION.md) for details.

## Docker

```bash
docker compose up --build
```

The provided Docker image is CPU-oriented. Native installation is currently recommended for NVIDIA GPU use.

## First EasyOCR run

EasyOCR downloads its recognition models the first time it is used. After the model is cached, OCR processing remains local.

## Accuracy guidance

OCR accuracy depends heavily on image acquisition. Use a tight crop, good focus, low-angle illumination for engraving, controlled exposure, and minimal glare. GPU acceleration improves speed, not recognition quality by itself.

## Security

The default server binds to localhost. Do not expose it directly to the internet. For network use, add authentication, TLS, request-size limits, and a reverse proxy. See [SECURITY.md](SECURITY.md).

## Roadmap

- PaddleOCR integration
- Batch processing
- User-selectable OCR language packs
- ONNX inference option
- Better result voting and format-aware validation
- Reproducible Windows/Linux release packaging

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and use GitHub Issues for bugs and proposals. Never upload confidential images or real identifiers.

## Support the project

After creating your funding profiles, update `.github/FUNDING.yml` and replace this section with your links. GitHub will display a **Sponsor** button when the funding file is valid.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

## Disclaimer

OCR output can be incorrect. Always verify recognized identifiers against the source image before using them for operational, legal, safety, or compliance decisions.
