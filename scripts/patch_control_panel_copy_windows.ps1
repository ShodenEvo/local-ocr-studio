$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (
    Split-Path -Parent $MyInvocation.MyCommand.Path
)

$BuildScript = Join-Path $Root "scripts\build_windows_executables.ps1"

if (-not (Test-Path $BuildScript)) {
    throw "Build script was not found: $BuildScript"
}

$Text = Get-Content `
    -Raw `
    -Encoding UTF8 `
    $BuildScript

$OldBlock = @'
Copy-Item `
    "$Dist\LocalOCRStudioControlPanel.exe" `
    "$Root\LocalOCRStudioControlPanel.exe" `
    -Force
'@

$NewBlock = @'
$ControlPanelSource = Join-Path `
    $Dist `
    "LocalOCRStudioControlPanel.exe"

$ControlPanelTarget = Join-Path `
    $Root `
    "LocalOCRStudioControlPanel.exe"

if (-not (Test-Path $ControlPanelSource)) {
    throw "Built control panel executable was not found: $ControlPanelSource"
}

$ControlPanelWasRunning = $false

$RunningControlPanels = Get-Process `
    -Name "LocalOCRStudioControlPanel" `
    -ErrorAction SilentlyContinue

if ($RunningControlPanels) {
    $ControlPanelWasRunning = $true

    Write-Host `
        "Closing the running Local OCR Studio control panel..." `
        -ForegroundColor Yellow

    $RunningControlPanels |
        Stop-Process -Force

    Start-Sleep -Milliseconds 750
}

$CopyAttempts = 0
$Copied = $false

while (-not $Copied -and $CopyAttempts -lt 10) {
    $CopyAttempts++

    try {
        Copy-Item `
            -Path $ControlPanelSource `
            -Destination $ControlPanelTarget `
            -Force `
            -ErrorAction Stop

        $Copied = $true
    }
    catch {
        if ($CopyAttempts -ge 10) {
            throw
        }

        Start-Sleep -Milliseconds 500
    }
}

if ($ControlPanelWasRunning) {
    Write-Host `
        "Restarting the Local OCR Studio control panel..." `
        -ForegroundColor Cyan

    Start-Process `
        -FilePath $ControlPanelTarget
}
'@

if ($Text.Contains($NewBlock)) {
    Write-Host "Build script is already patched." -ForegroundColor Green
    exit 0
}

if (-not $Text.Contains($OldBlock)) {
    throw "The expected control-panel Copy-Item block was not found. The script was not modified."
}

$Text = $Text.Replace($OldBlock, $NewBlock)

Set-Content `
    -Path $BuildScript `
    -Value $Text `
    -Encoding UTF8

Write-Host "Patched the control-panel copy step successfully." -ForegroundColor Green
