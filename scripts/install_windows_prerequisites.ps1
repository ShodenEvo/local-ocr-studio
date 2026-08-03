$ErrorActionPreference = "Stop"

function Test-Tesseract {
    $command = Get-Command tesseract.exe -ErrorAction SilentlyContinue
    $candidates = @(
        $(if ($command) { $command.Source }),
        "C:\Program Files\Tesseract-OCR\tesseract.exe",
        "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

$tesseract = Test-Tesseract

if (-not $tesseract) {
    Write-Host "Tesseract OCR is not installed." -ForegroundColor Yellow

    if (Get-Command winget.exe -ErrorAction SilentlyContinue) {
        $answer = Read-Host "Install Tesseract now using WinGet? [Y/n]"
        if ([string]::IsNullOrWhiteSpace($answer) -or $answer -match "^[Yy]") {
            winget install --exact --id UB-Mannheim.TesseractOCR `
                --accept-package-agreements `
                --accept-source-agreements
        }
    }
    else {
        Write-Host ""
        Write-Host "WinGet is unavailable." -ForegroundColor Yellow
        Write-Host "Install Tesseract manually under:"
        Write-Host "C:\Program Files\Tesseract-OCR"
    }
}

$tesseract = Test-Tesseract

if ($tesseract) {
    Write-Host "Tesseract detected: $tesseract" -ForegroundColor Green
    & $tesseract --version | Select-Object -First 1
}
else {
    Write-Warning "Tesseract remains unavailable. EasyOCR will still work."
    Write-Warning "Automatic ensemble mode will skip Tesseract."
}
