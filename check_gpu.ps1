Write-Host "=== NVIDIA driver ===" -ForegroundColor Cyan
nvidia-smi

Write-Host "`n=== PyTorch CUDA status inside this app ===" -ForegroundColor Cyan
.\venv\Scripts\python.exe -c "import torch; print('PyTorch:', torch.__version__); print('Built with CUDA:', torch.version.cuda); print('CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
