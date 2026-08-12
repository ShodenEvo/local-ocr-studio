$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root "venv\Scripts\python.exe"
$Dist = Join-Path $Root "dist\windows"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found: $Python"
}

Set-Location $Root

& $Python -m pip install --upgrade `
    pyinstaller `
    pywin32 `
    pystray

if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Windows build requirements."
}

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Dist
New-Item -ItemType Directory -Force $Dist | Out-Null

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "LocalOCRStudioControlPanel" `
    --distpath $Dist `
    --workpath "$Root\build\control-panel" `
    --specpath "$Root\build" `
    --hidden-import pystray._win32 `
    "$Root\windows\ocr_studio_control_panel.py"

if ($LASTEXITCODE -ne 0) {
    throw "Control panel build failed."
}

& dotnet publish `
    "$Root\windows\LocalOCRStudioService\LocalOCRStudioService.csproj" `
    -c Release `
    -r win-x64 `
    --self-contained true `
    /p:PublishSingleFile=true `
    /p:PublishTrimmed=false `
    -o "$Dist\LocalOCRStudioService"

if ($LASTEXITCODE -ne 0) {
    throw "Service executable build failed."
}

& dotnet publish `
    "$Root\windows\LocalOCRStudioInstaller\LocalOCRStudioInstaller.csproj" `
    -c Release `
    -r win-x64 `
    --self-contained true `
    /p:PublishSingleFile=true `
    /p:PublishTrimmed=false `
    -o "$Dist\LocalOCRStudioInstaller"

if ($LASTEXITCODE -ne 0) {
    throw "Installer executable build failed."
}

$ServiceBundleSource = Join-Path $Dist "LocalOCRStudioService"
$ServiceBundleTarget = Join-Path $Root "service"
$ServiceExecutable = Join-Path $ServiceBundleTarget "LocalOCRStudioService.exe"

if (-not (Test-Path $ServiceBundleSource)) {
    throw "Published service bundle was not found: $ServiceBundleSource"
}

Remove-Item `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue `
    $ServiceBundleTarget

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ServiceBundleTarget |
    Out-Null

Copy-Item `
    -Path (Join-Path $ServiceBundleSource "*") `
    -Destination $ServiceBundleTarget `
    -Recurse `
    -Force

if (-not (Test-Path $ServiceExecutable)) {
    throw "Built service executable was not copied to: $ServiceExecutable"
}

$ControlPanelSource = Join-Path `
    $Dist `
    "LocalOCRStudioControlPanel.exe"

$ControlPanelTarget = Join-Path `
    $Root `
    "LocalOCRStudioControlPanel.exe"

$InstallerSource = Join-Path `
    $Dist `
    "LocalOCRStudioInstaller"

$InstallerExecutable = Join-Path $InstallerSource "LocalOCRStudioInstaller.exe"
$InstallerTarget = Join-Path $Root "LocalOCRStudioInstaller.exe"

if (-not (Test-Path $ControlPanelSource)) {
    throw "Built control panel executable was not found: $ControlPanelSource"
}

if (-not (Test-Path $InstallerExecutable)) {
    throw "Built installer executable was not found: $InstallerExecutable"
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

Copy-Item `
    -Path $InstallerExecutable `
    -Destination $InstallerTarget `
    -Force `

# Remove the obsolete root-level service executable to prevent accidental
# registration of the old one-file build.
Remove-Item `
    -Force `
    -ErrorAction SilentlyContinue `
    "$Root\LocalOCRStudioService.exe"

Write-Host ""
Write-Host "Windows executables built successfully:" -ForegroundColor Green
Write-Host "  $Root\LocalOCRStudioControlPanel.exe"
Write-Host "  $ServiceExecutable"
Write-Host "  $InstallerTarget"

