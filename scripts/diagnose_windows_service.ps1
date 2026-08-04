$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent (
    Split-Path -Parent $MyInvocation.MyCommand.Path
)

Write-Host "Local OCR Studio service diagnostics" -ForegroundColor Cyan
Write-Host "Project: $Root"
Write-Host ""

$ServiceExe = Join-Path $Root "service\LocalOCRStudioService.exe"
$Python = Join-Path $Root "venv\Scripts\python.exe"
$Main = Join-Path $Root "app\main.py"

Write-Host "Service executable: $(Test-Path $ServiceExe) - $ServiceExe"
Write-Host "Python:             $(Test-Path $Python) - $Python"
Write-Host "Application:        $(Test-Path $Main) - $Main"
Write-Host ""

Get-CimInstance Win32_Service `
    -Filter "Name='LocalOCRStudio'" |
    Select-Object Name, State, StartMode, StartName, PathName

Write-Host ""
Write-Host "Recent Service Control Manager events:" -ForegroundColor Cyan

Get-WinEvent `
    -FilterHashtable @{
        LogName = "System"
        ProviderName = "Service Control Manager"
        StartTime = (Get-Date).AddMinutes(-30)
    } `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Message -match "LocalOCRStudio|Local OCR Studio"
    } |
    Select-Object TimeCreated, Id, LevelDisplayName, Message |
    Format-List

Write-Host ""
Write-Host "Recent application events:" -ForegroundColor Cyan

Get-WinEvent `
    -FilterHashtable @{
        LogName = "Application"
        StartTime = (Get-Date).AddMinutes(-30)
    } `
    -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Message -match "LocalOCRStudio|Local OCR Studio|Python Service"
    } |
    Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, Message |
    Format-List

$Log = Join-Path $Root "logs\service.log"

if (Test-Path $Log) {
    Write-Host ""
    Write-Host "Latest service.log lines:" -ForegroundColor Cyan
    Get-Content $Log -Tail 100
}


Write-Host ""
Write-Host "Expected service project root:" -ForegroundColor Cyan
Write-Host $Root
Write-Host "Expected runtime Python:"
Write-Host (Join-Path $Root "venv\Scripts\python.exe")
