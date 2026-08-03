$ErrorActionPreference = "Stop"

function Find-Tesseract {
    $Command = Get-Command `
        tesseract.exe `
        -ErrorAction SilentlyContinue

    $Candidates = @()

    if ($Command) {
        $Candidates += $Command.Source
    }

    $Candidates += @(
        "C:\Program Files\Tesseract-OCR\tesseract.exe",
        "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    )

    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path $Candidate)) {
            return $Candidate
        }
    }

    return $null
}


$Tesseract = Find-Tesseract

if (-not $Tesseract) {
    Write-Host `
        "Tesseract OCR is not installed." `
        -ForegroundColor Yellow

    $Winget = Get-Command `
        winget.exe `
        -ErrorAction SilentlyContinue

    if ($Winget) {
        $Answer = Read-Host `
            "Install Tesseract using WinGet? [Y/n]"

        if (
            [string]::IsNullOrWhiteSpace($Answer) `
            -or $Answer -match "^[Yy]"
        ) {
            winget install `
                --exact `
                --id UB-Mannheim.TesseractOCR `
                --accept-package-agreements `
                --accept-source-agreements
        }
    }
    else {
        Write-Host `
            "WinGet is unavailable." `
            -ForegroundColor Yellow

        Write-Host "Install Tesseract manually under:"
        Write-Host "C:\Program Files\Tesseract-OCR"
    }
}

$Tesseract = Find-Tesseract

if ($Tesseract) {
    Write-Host `
        "Tesseract detected: $Tesseract" `
        -ForegroundColor Green

    & $Tesseract --version |
        Select-Object -First 1
}
else {
    Write-Warning "Tesseract remains unavailable."
    Write-Warning "EasyOCR will still work."
    Write-Warning "Automatic ensemble mode will skip Tesseract."
}
