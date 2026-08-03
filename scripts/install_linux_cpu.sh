#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
if command -v apt-get >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y python3-venv tesseract-ocr libgl1 libglib2.0-0
fi
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip wheel
venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
venv/bin/python -m pip install -r requirements.txt
echo "CPU installation complete."
