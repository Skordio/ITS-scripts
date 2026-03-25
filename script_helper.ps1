function Activate-Venv {
    Write-Host "Activating virtual environment..."
    try {
        .venv/Scripts/Activate.ps1
    } catch {
        .venv/bin/Activate.ps1
    }
}

function Create-Venv {
    Write-Host "Creating virtual environment..."
    python3 -m venv .venv
}

function Setup-Venv {
    if (-Not (Test-Path -Path ".venv")) {
        Create-Venv
    }
    Activate-Venv
}

function Initialize-ITSRuntime {
    param(
        [switch]$SkipGitPull,
        [switch]$SkipRequirementsInstall
    )

    Set-Location $PSScriptRoot

    if (-Not $SkipGitPull) {
        git pull -q
    }

    try {
        Setup-Venv
    } catch {
        Write-Host "Failed to set up virtual environment. Please check for errors and try again."
        exit 1
    }

    if ((-Not $SkipRequirementsInstall) -and $env:VIRTUAL_ENV) {
        Write-Host "Ensuring requirements are installed..."
        pip install -q -r requirements.txt
    }

    Write-Host ""
}

function Invoke-ITSProgram {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProgramPath,
        [string[]]$ProgramArgs = @()
    )

    python3 $ProgramPath @ProgramArgs
}
