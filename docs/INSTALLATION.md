# Installation

## Supported platforms

- Windows 10/11, Python 3.11–3.12
- Ubuntu/Debian-derived Linux, Python 3.11–3.12
- CPU mode on both platforms
- Optional NVIDIA CUDA acceleration for EasyOCR

## Windows CPU

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_cpu.ps1
.\scripts\start_windows.ps1
```

## Windows NVIDIA

Install a current NVIDIA driver, then:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows_nvidia.ps1
.\scripts\start_windows.ps1
```

## Linux CPU

```bash
chmod +x scripts/*.sh
./scripts/install_linux_cpu.sh
./scripts/start_linux.sh
```

## Linux NVIDIA

Install a compatible NVIDIA driver first, confirm `nvidia-smi`, then:

```bash
chmod +x scripts/*.sh
./scripts/install_linux_nvidia.sh
./scripts/start_linux.sh
```

Open `http://127.0.0.1:8095`.

EasyOCR downloads model files during first use. Internet is required for that first model download; subsequent processing is local.
