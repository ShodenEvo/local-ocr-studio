# Windows service error 1053 fix

This update fixes a frozen pywin32 service that installs successfully but
fails with:

```text
The service did not respond to the start or control request in a timely fashion.
```

## Changes

- Uses the explicit Service Control Manager dispatcher when the executable is
  started without command-line arguments.
- Builds the service as a PyInstaller `onedir` bundle for faster and more
  predictable service startup.
- Installs the service from `service\LocalOCRStudioService.exe`.
- Adds Windows event and service-log diagnostics.
- Keeps the tray control panel as a single executable.

## Rebuild and reinstall

Open PowerShell as Administrator:

```powershell
cd C:\dev\local-ocr-studio
Set-ExecutionPolicy -Scope Process Bypass

Get-Service LocalOCRStudio -ErrorAction SilentlyContinue |
    Stop-Service -Force -ErrorAction SilentlyContinue

sc.exe delete LocalOCRStudio

.\scripts\build_windows_executables.ps1
.\scripts\install_windows_service.ps1
```

Verify:

```powershell
Get-Service LocalOCRStudio
Invoke-WebRequest http://127.0.0.1:8095/api/status
```

Run diagnostics when needed:

```powershell
.\scripts\diagnose_windows_service.ps1
```
