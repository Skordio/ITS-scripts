cd $PSScriptRoot
git pull -q

# If files were updated, we need to re-run the script to ensure the venv is set up correctly
# if ($LASTEXITCODE -ne 0) {
#     Write-Host "Files were updated, restarting script to ensure virtual environment is set up correctly..."
#     & $MyInvocation.MyCommand.Path @args
#     exit 0
# }


### VENV ###
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

try {
    Setup-Venv
} catch {
    Write-Host "Failed to set up virtual environment. Please check for errors and try again."
    exit 1
}

# Only install requirements if the venv is successfully activated
if ($env:VIRTUAL_ENV) {
    Write-Host "Ensuring requirements are installed..."
    pip install -q -r requirements.txt
}


python3 programs/lib_drive_dist/run.py @args