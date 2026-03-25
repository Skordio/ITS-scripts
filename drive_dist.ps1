. "$PSScriptRoot/script_helper.ps1"

Initialize-ITSRuntime
Invoke-ITSProgram -ProgramPath "programs/lib_drive_dist/run.py" -ProgramArgs $args
