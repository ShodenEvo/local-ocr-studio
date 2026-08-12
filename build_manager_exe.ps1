$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$PythonCommand = $null
$PythonArgs = @()

if (Test-Path $VenvPython) {
    $PythonCommand = $VenvPython
}
else {
    if (Get-Command python.exe -ErrorAction SilentlyContinue) {
        $PythonCommand = "python.exe"
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonCommand = "python"
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonCommand = "py"
        $PythonArgs += "-3"
    }
}

if (-not $PythonCommand) {
    throw "Python interpreter not found. Create the project virtual environment or install Python on PATH. Expected venv: $VenvPython"
}

Set-Location $ProjectRoot

& $PythonCommand @PythonArgs -m pip install --upgrade pyinstaller

& $PythonCommand @PythonArgs -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "OCRStudioManager" `
    "$ProjectRoot\ocr_studio_manager.py"

$BuiltExe = Join-Path $ProjectRoot "dist\OCRStudioManager.exe"
$Destination = Join-Path $ProjectRoot "OCRStudioManager.exe"

if (-not (Test-Path $BuiltExe)) {
    throw "Build failed: $BuiltExe was not created."
}

Copy-Item $BuiltExe $Destination -Force

Write-Host ""
Write-Host "Manager rebuilt successfully:" -ForegroundColor Green
Write-Host $Destination
