# Control panel build copy fix v6

This is a targeted patch. It does not replace the entire build script and does
not reintroduce older service-build changes.

It changes only the copy step for:

```text
LocalOCRStudioControlPanel.exe
```

The patched build script now:

1. Detects whether the tray control panel is running.
2. Stops the running control-panel process.
3. Retries the executable copy if Windows briefly keeps the file locked.
4. Restarts the control panel only when it was running before the build.

## Apply

Copy this patch into the Local OCR Studio project, then run:

```powershell
cd C:\dev\local-ocr-studio
Set-ExecutionPolicy -Scope Process Bypass

.\scripts\patch_control_panel_copy_windows.ps1
```

Then rebuild:

```powershell
.\scripts\build_windows_executables.ps1
```
