$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (
    Split-Path -Parent $MyInvocation.MyCommand.Path
)

$ModelsDirectory = Join-Path $Root "models"
$ModelPath = Join-Path $ModelsDirectory "EDSR_x2.pb"
$ModelUrl = "https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb"
$Python = Join-Path $Root "venv\Scripts\python.exe"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ModelsDirectory |
    Out-Null

if (-not (Test-Path $Python)) {
    throw "The project virtual environment was not found: $Python"
}

$OpenCVCheck = @"
import cv2

print("OpenCV:", cv2.__version__)
print("dnn_superres:", hasattr(cv2, "dnn_superres"))

if not hasattr(cv2, "dnn_superres"):
    raise SystemExit(
        "OpenCV dnn_superres is unavailable. "
        "Run scripts\\normalize_opencv_windows.ps1 first."
    )
"@

& $Python -c $OpenCVCheck

if ($LASTEXITCODE -ne 0) {
    throw "OpenCV contrib verification failed."
}

Write-Host ""
Write-Host "Downloading EDSR x2 model..." -ForegroundColor Cyan
Write-Host $ModelUrl

$Downloaded = $false

if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
    & curl.exe `
        -L `
        --fail `
        --retry 5 `
        --retry-delay 3 `
        --connect-timeout 30 `
        -o $ModelPath `
        $ModelUrl

    if ($LASTEXITCODE -eq 0) {
        $Downloaded = $true
    }
}

if (-not $Downloaded) {
    Write-Host `
        "curl.exe failed or was unavailable. Trying Invoke-WebRequest..." `
        -ForegroundColor Yellow

    try {
        $ProgressPreference = "SilentlyContinue"

        Invoke-WebRequest `
            -UseBasicParsing `
            -Uri $ModelUrl `
            -OutFile $ModelPath

        if (Test-Path $ModelPath) {
            $Downloaded = $true
        }
    }
    catch {
        Write-Warning $_
    }
}

if (-not $Downloaded) {
    throw "EDSR model download failed."
}

if (-not (Test-Path $ModelPath)) {
    throw "The model file was not created: $ModelPath"
}

$File = Get-Item $ModelPath

if ($File.Length -lt 1000000) {
    Remove-Item -Force $ModelPath
    throw "The downloaded file is unexpectedly small or incomplete."
}

$ModelCheck = @"
import cv2
from pathlib import Path

model = Path(r"$ModelPath")

sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(str(model))
sr.setModel("edsr", 2)

print("Model loaded successfully:", model)
print("Model size:", model.stat().st_size, "bytes")
print("OpenCV:", cv2.__version__)
"@

& $Python -c $ModelCheck

if ($LASTEXITCODE -ne 0) {
    throw "The model was downloaded but OpenCV could not load it."
}

Write-Host ""
Write-Host "AI super-resolution model installed successfully." `
    -ForegroundColor Green
Write-Host "Model: $ModelPath"
Write-Host ""
Write-Host "Restart Local OCR Studio to refresh the status badge."
