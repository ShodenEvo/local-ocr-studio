from __future__ import annotations

import platform
import sys

print("Python:", sys.version.split()[0])
print("OS:", platform.platform())

try:
    import torch
except Exception as exc:
    print("PyTorch: unavailable")
    print("Error:", exc)
    raise SystemExit(1)

available = bool(torch.cuda.is_available())
hip = getattr(torch.version, "hip", None)
cuda = torch.version.cuda
backend = "ROCm" if available and hip else "CUDA" if available and cuda else "CPU"

print("PyTorch:", torch.__version__)
print("GPU available:", available)
print("Backend:", backend)
print("CUDA runtime:", cuda)
print("HIP runtime:", hip)
print("Device count:", torch.cuda.device_count() if available else 0)
print("Device:", torch.cuda.get_device_name(0) if available else "CPU mode")
