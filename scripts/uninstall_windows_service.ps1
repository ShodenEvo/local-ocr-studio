$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ServiceExe = Join-Path $Root "service\LocalOCRStudioService.exe"

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

if (Test-Path $ServiceExe) {
    & $ServiceExe --uninstall
}
else {
    sc.exe stop LocalOCRStudio 2>$null
    sc.exe delete LocalOCRStudio
}

$Shortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\Local OCR Studio Control Panel.lnk"
Remove-Item -Force -ErrorAction SilentlyContinue $Shortcut

Write-Host "Local OCR Studio service removed." -ForegroundColor Green
