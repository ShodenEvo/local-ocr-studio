$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
& "$Root\scripts\install_windows_prerequisites.ps1"
if (-not (Test-Path ".\venv\Scripts\python.exe")) { py -3 -m venv venv }
$Python = ".\venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip wheel
& $Python -m pip uninstall -y torch torchvision torchaudio
& $Python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
& $Python -m pip install -r requirements.txt
& $Python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU mode')"
Write-Host "NVIDIA installation complete." -ForegroundColor Green
