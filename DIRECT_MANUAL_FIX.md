# Direct manual fix

Open:

```text
C:\dev\local-ocr-studio\scripts\build_windows_executables.ps1
```

Find:

```powershell
Copy-Item `
    "$Dist\LocalOCRStudioControlPanel.exe" `
    "$Root\LocalOCRStudioControlPanel.exe" `
    -Force
```

Replace it with:

```powershell
$ControlPanelSource = Join-Path `
    $Dist `
    "LocalOCRStudioControlPanel.exe"

$ControlPanelTarget = Join-Path `
    $Root `
    "LocalOCRStudioControlPanel.exe"

$ControlPanelWasRunning = $false

$RunningControlPanels = Get-Process `
    -Name "LocalOCRStudioControlPanel" `
    -ErrorAction SilentlyContinue

if ($RunningControlPanels) {
    $ControlPanelWasRunning = $true
    $RunningControlPanels | Stop-Process -Force
    Start-Sleep -Milliseconds 750
}

Copy-Item `
    -Path $ControlPanelSource `
    -Destination $ControlPanelTarget `
    -Force

if ($ControlPanelWasRunning) {
    Start-Process `
        -FilePath $ControlPanelTarget
}
```
