$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ServiceExe = Join-Path $Root "service\LocalOCRStudioService.exe"
$ManagerExe = Join-Path $Root "LocalOCRStudioControlPanel.exe"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Start-Process powershell.exe `
        -Verb RunAs `
        -WorkingDirectory $Root `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", ('"' + $MyInvocation.MyCommand.Path + '"')
        )
    exit
}

if (-not (Test-Path $ServiceExe)) {
    throw "Service executable not found. Run scripts\build_windows_executables.ps1 first."
}

Set-Location $Root

& $ServiceExe stop 2>$null
& $ServiceExe remove 2>$null
Start-Sleep -Seconds 1
& $ServiceExe --startup auto install
& $ServiceExe start

if (Test-Path $ManagerExe) {
    $Startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
    New-Item -ItemType Directory -Force $Startup | Out-Null
    $Shortcut = Join-Path $Startup "Local OCR Studio Control Panel.lnk"
    $Shell = New-Object -ComObject WScript.Shell
    $Link = $Shell.CreateShortcut($Shortcut)
    $Link.TargetPath = $ManagerExe
    $Link.WorkingDirectory = $Root
    $Link.Arguments = "--tray"
    $Link.Description = "Local OCR Studio background control panel"
    $Link.Save()
}

Write-Host ""
Write-Host "Local OCR Studio service installed and started." -ForegroundColor Green
Write-Host "Service name: LocalOCRStudio"
Write-Host "Web interface: http://127.0.0.1:8095"
