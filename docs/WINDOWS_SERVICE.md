# Windows service and control panel

Local OCR Studio can run automatically in the background as a native Windows service.

## Components

- `LocalOCRStudioService.exe` runs Uvicorn and the OCR application in Session 0.
- `LocalOCRStudioControlPanel.exe` provides a desktop control panel and system-tray icon.
- Closing the control panel minimizes it to the tray. It does not stop the service.
- Service output is stored in `logs/service.log`.

## Build on Windows

Complete the normal Windows installation first, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_windows_executables.ps1
```

The build creates:

```text
LocalOCRStudioControlPanel.exe
LocalOCRStudioService.exe
```

The executables must remain in the project root because the service uses the adjacent `venv`, `app`, `models`, and `logs` directories.

## Install the service

```powershell
.\scripts\install_windows_service.ps1
```

The installer requests administrator rights, installs the service with automatic startup, starts it, and adds the control panel to the current user's Startup folder in tray mode.

## Remove the service

```powershell
.\scripts\uninstall_windows_service.ps1
```

## Manual service commands

Run these from an elevated PowerShell window:

```powershell
.\LocalOCRStudioService.exe --startup auto install
.\LocalOCRStudioService.exe start
.\LocalOCRStudioService.exe stop
.\LocalOCRStudioService.exe restart
.\LocalOCRStudioService.exe remove
```

## Network binding

The service defaults to:

```text
OCR_HOST=127.0.0.1
OCR_PORT=8095
```

The default is local-only. To expose it to a trusted LAN, set system environment variables and restart the service:

```powershell
[Environment]::SetEnvironmentVariable("OCR_HOST", "0.0.0.0", "Machine")
[Environment]::SetEnvironmentVariable("OCR_PORT", "8095", "Machine")
Restart-Service LocalOCRStudio
```

Exposing the service to a network should be combined with Windows Firewall restrictions and an authentication or reverse-proxy layer.

## Troubleshooting

Check:

```powershell
Get-Service LocalOCRStudio
Get-Content .\logs\service.log -Tail 100
```

The Windows Event Viewer also records service startup failures under Windows Logs → Application.
