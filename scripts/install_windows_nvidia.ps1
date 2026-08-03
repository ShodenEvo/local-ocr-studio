$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (
    Split-Path -Parent $MyInvocation.MyCommand.Path
)

Set-Location $Root

. "$Root\scripts\windows_common.ps1"

& "$Root\scripts\install_windows_prerequisites.ps1"

$Python = New-ProjectVirtualEnvironment `
    -ProjectRoot $Root

& $Python -m pip install `
    --upgrade `
    pip `
    wheel `
    setuptools

& $Python -m pip uninstall `
    -y `
    torch `
    torchvision `
    torchaudio

& $Python -m pip install `
    torch `
    torchvision `
    --index-url https://download.pytorch.org/whl/cu130

& $Python -m pip install `
    -r "$Root\requirements.txt"

& $Python -c @'
import torch

print("PyTorch:", torch.__version__)
print("CUDA build:", torch.version.cuda)
print("CUDA available:", torch.cuda.is_available())
print(
    "GPU:",
    torch.cuda.get_device_name(0)
    if torch.cuda.is_available()
    else "CPU mode",
)

if not torch.cuda.is_available():
    raise SystemExit(
        "CUDA is not active. Check the NVIDIA driver and PyTorch build."
    )
'@

Write-Host ""
Write-Host `
    "NVIDIA installation complete." `
    -ForegroundColor Green

Write-Host "Start with:"
Write-Host ".\scripts\start_windows.ps1"
