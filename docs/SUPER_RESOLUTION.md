# AI Super-Resolution Model

Local OCR Studio supports an optional OpenCV DNN super-resolution stage using an EDSR x2 TensorFlow model.

## What is required

1. `opencv-contrib-python-headless` must be installed.
2. `EDSR_x2.pb` must exist under:

```text
models/EDSR_x2.pb
```

The application discovers that project-local path automatically. An absolute path may be supplied through `SUPERRES_MODEL_PATH`.

Do not install `opencv-python`, `opencv-python-headless`, and `opencv-contrib-python-headless` together. They all provide the same `cv2` namespace.

## Windows installation

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_superres_model_windows.ps1
```

## Linux installation

Run:

```bash
chmod +x scripts/install_superres_model_linux.sh
./scripts/install_superres_model_linux.sh
```

## Manual download

Model source:

```text
https://github.com/Saafke/EDSR_Tensorflow
```

Direct model URL:

```text
https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb
```

Windows:

```powershell
New-Item -ItemType Directory -Force .\models

curl.exe -L `
  --fail `
  --retry 5 `
  --retry-delay 3 `
  -o ".\models\EDSR_x2.pb" `
  "https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb"
```

Linux:

```bash
mkdir -p models

curl \
  --location \
  --fail \
  --retry 5 \
  --retry-delay 3 \
  --output models/EDSR_x2.pb \
  https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/models/EDSR_x2.pb
```

## Verification

Windows:

```powershell
.\venv\Scripts\python.exe -c "import cv2; from pathlib import Path; p=Path('models/EDSR_x2.pb'); sr=cv2.dnn_superres.DnnSuperResImpl_create(); sr.readModel(str(p)); sr.setModel('edsr',2); print('EDSR x2 ready:', p.resolve())"
```

Linux:

```bash
venv/bin/python -c "import cv2; from pathlib import Path; p=Path('models/EDSR_x2.pb'); sr=cv2.dnn_superres.DnnSuperResImpl_create(); sr.readModel(str(p)); sr.setModel('edsr',2); print('EDSR x2 ready:', p.resolve())"
```

## Custom location

Windows PowerShell:

```powershell
$env:SUPERRES_MODEL_PATH = "D:\AI\Models\EDSR_x2.pb"
$env:SUPERRES_MODEL_NAME = "edsr"
$env:SUPERRES_MODEL_SCALE = "2"
```

Linux:

```bash
export SUPERRES_MODEL_PATH="/opt/ocr-models/EDSR_x2.pb"
export SUPERRES_MODEL_NAME="edsr"
export SUPERRES_MODEL_SCALE="2"
```

## Licensing and attribution

The model repository is published under Apache License 2.0. Review the upstream repository and license before redistributing the model binary.

## Accuracy warning

Super resolution generates an estimated higher-resolution image. It does not recover information that was never captured and may reinforce incorrect strokes. Always compare OCR output against the original image.
