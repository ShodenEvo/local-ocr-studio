# Contributing

Thank you for helping improve Local OCR Studio.

## Before opening a pull request

1. Search existing issues.
2. Create or reference an issue for substantial changes.
3. Keep image processing, OCR engines, and UI code modular.
4. Do not commit private images, serial numbers, model caches, virtual environments, or generated executables.
5. Test on at least one supported platform.

## Development setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux: source venv/bin/activate
pip install -r requirements-dev.txt
```

Run tests and linting:

```bash
pytest
ruff check .
```

## Pull requests

Describe the problem, the implementation, test evidence, platform, Python version, and whether CPU/CUDA was used. Screenshots are welcome, but remove sensitive information first.

## GPU-related reports

Include the complete output of `python scripts/check_accelerator.py`, exact GPU model, driver version, and installation command. AMD ROCm reports must include the ROCm release and Linux distribution/kernel.
