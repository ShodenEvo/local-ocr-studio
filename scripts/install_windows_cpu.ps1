$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
& "$Root\scripts\install_windows_prerequisites.ps1"
if (-not (Test-Path ".\venv\Scripts\python.exe")) { py -3 -m venv venv }
$Python = ".\venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip wheel
& $Python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $Python -m pip install -r requirements.txt
Write-Host "CPU installation complete." -ForegroundColor Green
