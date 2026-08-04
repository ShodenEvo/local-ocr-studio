# Windows service project-root fix v3

The service now starts correctly under the Windows Service Control Manager,
but the one-folder executable previously treated the `service` directory as
the application root.

This caused it to look for:

```text
service\venv\Scripts\python.exe
```

instead of:

```text
venv\Scripts\python.exe
```

The service now checks both the executable directory and its parent, and
selects the directory containing:

```text
app\main.py
venv\Scripts\python.exe
```

## Rebuild and reinstall

Run PowerShell as Administrator:

```powershell
cd C:\dev\local-ocr-studio

sc.exe stop LocalOCRStudio
sc.exe delete LocalOCRStudio
Start-Sleep -Seconds 3

.\scripts\build_windows_executables.ps1

.\service\LocalOCRStudioService.exe `
  --startup auto `
  install

.\service\LocalOCRStudioService.exe start
```

Then verify:

```powershell
Get-Service LocalOCRStudio
Invoke-WebRequest http://127.0.0.1:8095/api/status
```
