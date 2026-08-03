#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v nvidia-smi >/dev/null || { echo "NVIDIA driver/nvidia-smi not found"; exit 1; }
if command -v apt-get >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y python3-venv tesseract-ocr libgl1 libglib2.0-0
fi
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip wheel
venv/bin/python -m pip uninstall -y torch torchvision torchaudio || true
venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
venv/bin/python -m pip install -r requirements.txt
venv/bin/python - <<'PY'
import torch
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU mode")
PY
