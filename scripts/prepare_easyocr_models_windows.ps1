$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (
    Split-Path -Parent $MyInvocation.MyCommand.Path
)

$Python = Join-Path $Root "venv\Scripts\python.exe"
$ModelDirectory = Join-Path $Root "models\easyocr"
$VerifyScript = Join-Path $env:TEMP "local_ocr_prepare_easyocr.py"

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python was not found: $Python"
}

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ModelDirectory |
    Out-Null

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:EASYOCR_MODULE_PATH = $ModelDirectory
$env:MODULE_PATH = $ModelDirectory

@'
import os
from pathlib import Path
import easyocr
import torch

model_dir = Path(os.environ["EASYOCR_MODULE_PATH"])
model_dir.mkdir(parents=True, exist_ok=True)

gpu = bool(torch.cuda.is_available())

print("Preparing EasyOCR models")
print("Directory:", model_dir)
print("CUDA available:", gpu)

reader = easyocr.Reader(
    ["en"],
    gpu=gpu,
    model_storage_directory=str(model_dir),
    user_network_directory=str(model_dir / "user_network"),
    download_enabled=True,
    verbose=False,
)

print("EasyOCR models are ready.")
print("Detector:", reader.detector is not None)
print("Recognizer:", reader.recognizer is not None)
'@ | Set-Content `
    -Path $VerifyScript `
    -Encoding UTF8

try {
    & $Python $VerifyScript

    if ($LASTEXITCODE -ne 0) {
        throw "EasyOCR model preparation failed."
    }
}
finally {
    Remove-Item `
        -Force `
        -ErrorAction SilentlyContinue `
        $VerifyScript
}

Write-Host ""
Write-Host "EasyOCR model installation completed." -ForegroundColor Green
Write-Host "Models: $ModelDirectory"
