$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$HostAddress = if ($env:OCR_HOST) { $env:OCR_HOST } else { "127.0.0.1" }
$Port = if ($env:OCR_PORT) { $env:OCR_PORT } else { "8095" }
& ".\venv\Scripts\python.exe" -m uvicorn app.main:app --host $HostAddress --port $Port
