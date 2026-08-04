$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (
    Split-Path -Parent $MyInvocation.MyCommand.Path
)

$ServiceSource = Join-Path $Root "windows\ocr_studio_service.py"

if (-not (Test-Path $ServiceSource)) {
    throw "Service source was not found: $ServiceSource"
}

$Text = Get-Content `
    -Raw `
    -Encoding UTF8 `
    $ServiceSource

$OldBlock = @'
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        command = [
'@

$NewBlock = @'
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Windows services normally inherit a legacy console encoding.
        # EasyOCR's download progress bar contains Unicode block characters,
        # so force the child Python runtime and redirected output to UTF-8.
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        # Keep EasyOCR models in the application directory. LocalSystem has a
        # different user profile and would otherwise use the system profile.
        easyocr_model_dir = self.root / "models" / "easyocr"
        easyocr_model_dir.mkdir(parents=True, exist_ok=True)
        env["EASYOCR_MODULE_PATH"] = str(easyocr_model_dir)
        env["MODULE_PATH"] = str(easyocr_model_dir)

        command = [
'@

if (-not $Text.Contains($OldBlock)) {
    if (
        $Text.Contains('env["PYTHONUTF8"] = "1"') -and
        $Text.Contains('env["EASYOCR_MODULE_PATH"]')
    ) {
        Write-Host "Service source is already patched." -ForegroundColor Green
        exit 0
    }

    throw "Expected service environment block was not found."
}

$Text = $Text.Replace($OldBlock, $NewBlock)

Set-Content `
    -Path $ServiceSource `
    -Value $Text `
    -Encoding UTF8

Write-Host "Patched Windows service environment successfully." `
    -ForegroundColor Green
Write-Host "EasyOCR model directory:"
Write-Host (Join-Path $Root "models\easyocr")
