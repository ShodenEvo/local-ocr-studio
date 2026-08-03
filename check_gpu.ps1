$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Virtual environment not found: $Python" }
& $Python (Join-Path $Root "scripts\check_accelerator.py")
