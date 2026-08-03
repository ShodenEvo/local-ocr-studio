$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found: $Python"
}

Set-Location $ProjectRoot

& $Python -m pip install --upgrade pyinstaller

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "OCRStudioManager" `
    "$ProjectRoot\ocr_studio_manager.py"

$BuiltExe = Join-Path $ProjectRoot "dist\OCRStudioManager.exe"
$Destination = Join-Path $ProjectRoot "OCRStudioManager.exe"

if (-not (Test-Path $BuiltExe)) {
    throw "Build failed: $BuiltExe was not created."
}

Copy-Item $BuiltExe $Destination -Force

Write-Host ""
Write-Host "Manager rebuilt successfully:" -ForegroundColor Green
Write-Host $Destination
