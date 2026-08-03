# AMD GPU Support

## Why AMD hardware may show CPU mode

EasyOCR uses PyTorch. Detecting an AMD display adapter does not mean that the installed PyTorch wheel supports that adapter.

The application reports hardware separately from the active backend.

## Linux AMD

ROCm is the preferred AMD GPU path on supported Linux systems.

Requirements depend on:

- Exact AMD GPU
- Linux distribution and kernel
- AMD driver and ROCm release
- Matching ROCm-enabled PyTorch wheel
- Supported Python version

Verify:

```python
import torch

print(torch.__version__)
print(torch.cuda.is_available())
print(torch.version.hip)
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
```

PyTorch uses the `torch.cuda` namespace for ROCm devices. That is expected.

## Windows AMD

The default supported configuration is CPU mode.

AMD publishes Windows ROCm/PyTorch support for selected hardware and software combinations, but it is not universal. EasyOCR must also be validated with the chosen build.

Therefore, the project does not silently replace a working CPU environment with an unverified Windows AMD package.

The UI message:

```text
AMD GPU detected — EasyOCR currently using CPU
```

is informational, not an application failure.

## DirectML

DirectML is not connected to EasyOCR in this release. Installing `torch-directml` alone does not cause EasyOCR to use it.

The planned broader Windows backend is ONNX Runtime with DirectML.

## Reporting an AMD issue

Include exact GPU, OS, driver, ROCm version where applicable, Python, PyTorch, installation command, and the output from `scripts/check_accelerator.py`.
