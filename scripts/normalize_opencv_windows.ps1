$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (
    Split-Path -Parent $MyInvocation.MyCommand.Path
)

$Python = Join-Path $Root "venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment was not found: $Python"
}

Write-Host "Normalizing OpenCV packages..." -ForegroundColor Cyan

& $Python -m pip uninstall -y `
    opencv-python `
    opencv-python-headless `
    opencv-contrib-python `
    opencv-contrib-python-headless

if ($LASTEXITCODE -ne 0) {
    throw "Failed while removing existing OpenCV packages."
}

& $Python -m pip install `
    "opencv-contrib-python-headless>=4.10"

if ($LASTEXITCODE -ne 0) {
    throw "Failed to install opencv-contrib-python-headless."
}

$VerificationScript = @"
import cv2

print("OpenCV:", cv2.__version__)
print("dnn_superres:", hasattr(cv2, "dnn_superres"))

if not hasattr(cv2, "dnn_superres"):
    raise SystemExit("dnn_superres is unavailable.")
"@

& $Python -c $VerificationScript

if ($LASTEXITCODE -ne 0) {
    throw "OpenCV contrib verification failed."
}

Write-Host ""
Write-Host "OpenCV contrib installation is ready." -ForegroundColor Green
