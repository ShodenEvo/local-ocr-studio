# Changelog

## Unreleased

- Fixed service project-root detection when running from the `service` bundle directory.

- Fixed Windows service error 1053 by entering the SCM dispatcher explicitly.
- Changed the service package from PyInstaller one-file to one-folder mode.
- Added Windows service diagnostic script and event-log inspection.

- Added a native Windows background service executable.
- Added a Windows system-tray control panel executable.
- Added build, install, repair, and uninstall scripts for the service.
- Added automatic-start shortcut support for the control panel.
- Added persistent service logging under `logs/service.log`.

- Switched the OpenCV dependency to `opencv-contrib-python-headless` for `dnn_superres`.
- Added Windows and Linux EDSR x2 model installation scripts.
- Added automatic discovery of `models/EDSR_x2.pb`.
- Added model download, verification, licensing, and troubleshooting documentation.
- Added optional super-resolution environment variables to `.env.example`.

- Added consensus-based OCR selection instead of confidence-only ranking.
- Added expected text length and mixed-alphanumeric controls.
- Added clickable manual result selection.
- Added grayscale engraving-relief enhancement.
- Disabled AI super-resolution when no model is configured.
- Penalized destructive threshold and strong-restoration paths.

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
