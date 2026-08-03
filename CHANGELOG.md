# Changelog

## Unreleased

- Added Manual and Automatic restoration/upscale modes.
- Added original-versus-restored OCR comparison and restoration source labels.
- Added conservative deblur, denoise, deblocking, and Lanczos upscale paths.
- Added optional OpenCV DNN AI super-resolution model support.

- Added Windows Tesseract prerequisite detection and optional WinGet installation.
- Added an explicit Windows AMD installer with reliable CPU fallback.
- Added hardware-aware AMD/NVIDIA status messages.
- Automatic ensemble OCR now skips unavailable engines instead of failing.
- Expanded README requirements and troubleshooting.

All notable changes will be documented here.

## [Unreleased]

### Added
- AMD ROCm acceleration on compatible Linux systems.
- Generic CUDA/ROCm/CPU accelerator reporting.
- AMD installation and troubleshooting documentation.
- Linux AMD ROCm installer and accelerator diagnostic script.

### Clarified
- Windows AMD uses supported CPU mode; DirectML acceleration remains experimental.

### Added
- Cross-platform Windows and Linux installation scripts.
- Tesseract, EasyOCR, OpenCV enhancement, and CUDA status reporting.
- Web interface with cropping, enhancement selection, ensemble OCR, and confidence display.
