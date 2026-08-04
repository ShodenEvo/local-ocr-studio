#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="$ROOT/models"
MODEL_PATH="$MODELS_DIR/EDSR_x2.pb"
MODEL_URL="https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb"
PYTHON="$ROOT/venv/bin/python"

mkdir -p "$MODELS_DIR"

if command -v curl >/dev/null 2>&1; then
    curl \
        --location \
        --fail \
        --retry 5 \
        --retry-delay 3 \
        --connect-timeout 30 \
        --output "$MODEL_PATH" \
        "$MODEL_URL"
elif command -v wget >/dev/null 2>&1; then
    wget \
        --tries=5 \
        --timeout=30 \
        --output-document="$MODEL_PATH" \
        "$MODEL_URL"
else
    echo "Install curl or wget before downloading the model." >&2
    exit 1
fi

FILE_SIZE="$(wc -c < "$MODEL_PATH")"

if [ "$FILE_SIZE" -lt 1000000 ]; then
    rm -f "$MODEL_PATH"
    echo "Downloaded file is unexpectedly small or incomplete." >&2
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "Virtual environment not found. Run the app installer first." >&2
    exit 1
fi

"$PYTHON" - "$MODEL_PATH" <<'PY'
import sys
from pathlib import Path
import cv2

model = Path(sys.argv[1])

if not hasattr(cv2, "dnn_superres"):
    raise SystemExit(
        "OpenCV dnn_superres is unavailable. Install "
        "opencv-contrib-python-headless and remove other OpenCV wheels."
    )

sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(str(model))
sr.setModel("edsr", 2)

print("Model loaded successfully:", model)
print("OpenCV:", cv2.__version__)
PY

echo
echo "AI super-resolution model installed:"
echo "$MODEL_PATH"
echo
echo "Restart Local OCR Studio to refresh the status badge."
