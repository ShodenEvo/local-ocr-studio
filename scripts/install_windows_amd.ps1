$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

& "$Root\scripts\install_windows_prerequisites.ps1"

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    py -3 -m venv venv
}

$Python = ".\venv\Scripts\python.exe"

& $Python -m pip install --upgrade pip wheel
& $Python -m pip uninstall -y torch torchvision torchaudio
& $Python -m pip install torch torchvision `
    --index-url https://download.pytorch.org/whl/cpu
& $Python -m pip install -r requirements.txt

Write-Host ""
Write-Host "Windows AMD installation completed in supported CPU mode." `
    -ForegroundColor Green
Write-Host ""
Write-Host "EasyOCR uses PyTorch. AMD GPU acceleration on Windows depends on"
Write-Host "the exact Radeon model and an AMD-supported ROCm/PyTorch build."
Write-Host "This installer does not replace a working CPU environment with an"
Write-Host "unverified GPU package."
Write-Host ""
Write-Host "See docs\AMD_GPU.md for the experimental Windows ROCm path."
