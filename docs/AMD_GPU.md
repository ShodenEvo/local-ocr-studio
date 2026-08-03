# AMD GPU Support

## Linux: ROCm

Local OCR Studio supports EasyOCR acceleration through a ROCm-enabled PyTorch build on compatible AMD GPUs. PyTorch uses the `torch.cuda` Python namespace for CUDA and ROCm devices, so this is expected:

```python
import torch
print(torch.cuda.is_available())
print(torch.version.hip)
print(torch.cuda.get_device_name(0))
```

A working environment should report:

```text
GPU available: True
Backend: ROCm
HIP runtime: <version>
Device: AMD Radeon ...
```

ROCm compatibility depends on the exact GPU, distribution, kernel, driver, Python, ROCm, and PyTorch versions. Check AMD's current matrix before reporting an application bug.

## Windows: AMD

CPU mode is supported. DirectML can accelerate PyTorch workloads across DirectX 12 GPUs, but EasyOCR does not currently expose a dependable DirectML device path in this project. Windows AMD acceleration is therefore marked **experimental/not enabled**, rather than being presented as working.

An ONNX Runtime backend is the preferred future route for broad Windows AMD and Intel acceleration.

## Reporting an AMD issue

Attach the output of:

```bash
python scripts/check_accelerator.py
```

Include the exact GPU, OS/kernel, AMD driver, ROCm, PyTorch, Python, and installation command. Do not attach confidential images.
