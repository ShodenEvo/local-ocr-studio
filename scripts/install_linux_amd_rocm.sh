#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
command -v rocminfo >/dev/null || {
  echo "ROCm/rocminfo was not found. Install a ROCm release supported by your AMD GPU and OS first."
  exit 1
}

if [[ -z "${PYTORCH_ROCM_INDEX_URL:-}" ]]; then
  cat <<'EOF'
PYTORCH_ROCM_INDEX_URL is required.
Use the official PyTorch Start Locally selector and choose Linux / Pip / Python / ROCm.
Example placeholder only:
  export PYTORCH_ROCM_INDEX_URL="https://download.pytorch.org/whl/rocmX.Y"
Use the version matching your installed ROCm release.
EOF
  exit 2
fi

if command -v apt-get >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y python3-venv tesseract-ocr libgl1 libglib2.0-0
fi

python3 -m venv venv
venv/bin/python -m pip install --upgrade pip wheel
venv/bin/python -m pip uninstall -y torch torchvision torchaudio || true
venv/bin/python -m pip install torch torchvision --index-url "$PYTORCH_ROCM_INDEX_URL"
venv/bin/python -m pip install -r requirements.txt
venv/bin/python scripts/check_accelerator.py

venv/bin/python -c 'import torch; assert torch.cuda.is_available() and getattr(torch.version, "hip", None), "ROCm GPU not detected"; print("AMD ROCm installation complete.")'
