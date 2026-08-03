$ErrorActionPreference = "Stop"

function Find-SupportedPython {
    $Candidates = @(
        @{
            Name = "Python launcher 3.12"
            FilePath = "py"
            PrefixArguments = @("-3.12")
        },
        @{
            Name = "Python launcher 3.11"
            FilePath = "py"
            PrefixArguments = @("-3.11")
        },
        @{
            Name = "Python 3.12 per-user install"
            FilePath = (
                Join-Path $env:LOCALAPPDATA `
                    "Programs\Python\Python312\python.exe"
            )
            PrefixArguments = @()
        },
        @{
            Name = "Python 3.12 system install"
            FilePath = "C:\Program Files\Python312\python.exe"
            PrefixArguments = @()
        },
        @{
            Name = "Python 3.11 per-user install"
            FilePath = (
                Join-Path $env:LOCALAPPDATA `
                    "Programs\Python\Python311\python.exe"
            )
            PrefixArguments = @()
        },
        @{
            Name = "Python 3.11 system install"
            FilePath = "C:\Program Files\Python311\python.exe"
            PrefixArguments = @()
        },
        @{
            Name = "python from PATH"
            FilePath = "python"
            PrefixArguments = @()
        },
        @{
            Name = "python3 from PATH"
            FilePath = "python3"
            PrefixArguments = @()
        }
    )

    foreach ($Candidate in $Candidates) {
        $FilePath = $Candidate.FilePath
        $PrefixArguments = $Candidate.PrefixArguments

        if (
            $FilePath -match "[\\/]" `
            -and -not (Test-Path $FilePath)
        ) {
            continue
        }

        if (
            $FilePath -notmatch "[\\/]" `
            -and -not (
                Get-Command $FilePath -ErrorAction SilentlyContinue
            )
        ) {
            continue
        }

        try {
            $Version = & $FilePath @PrefixArguments -c `
                "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"

            if ($LASTEXITCODE -ne 0) {
                continue
            }

            $Version = "$Version".Trim()

            if ($Version -in @("3.11", "3.12")) {
                return @{
                    Name = $Candidate.Name
                    FilePath = $FilePath
                    PrefixArguments = $PrefixArguments
                    Version = $Version
                }
            }
        }
        catch {
            continue
        }
    }

    throw @"
Python 3.11 or Python 3.12 was not found.

Install Python 3.12:

    winget install --exact --id Python.Python.3.12

Then close PowerShell, open a new PowerShell window, and verify:

    py -3.12 --version

You can also create the virtual environment manually:

    py -3.12 -m venv venv
"@
}


function New-ProjectVirtualEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $VenvPath = Join-Path $ProjectRoot "venv"
    $VenvPython = Join-Path $VenvPath "Scripts\python.exe"

    if (Test-Path $VenvPython) {
        $Version = & $VenvPython -c `
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"

        $Version = "$Version".Trim()

        if ($Version -in @("3.11", "3.12")) {
            Write-Host `
                "Existing virtual environment uses Python $Version." `
                -ForegroundColor Green

            return $VenvPython
        }

        Write-Host `
            "Removing incompatible virtual environment (Python $Version)..." `
            -ForegroundColor Yellow

        Remove-Item -Recurse -Force $VenvPath
    }

    $Python = Find-SupportedPython
    $Prefix = $Python.PrefixArguments

    Write-Host `
        "Creating virtual environment using $($Python.Name) ($($Python.Version))..." `
        -ForegroundColor Cyan

    & $Python.FilePath @Prefix -m venv $VenvPath

    if ($LASTEXITCODE -ne 0) {
        throw "Python failed to create the virtual environment."
    }

    if (-not (Test-Path $VenvPython)) {
        throw "Virtual environment was not created at: $VenvPath"
    }

    return $VenvPython
}
