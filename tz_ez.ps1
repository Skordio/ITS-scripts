. "$PSScriptRoot/script_helper.ps1"

Initialize-ITSRuntime
Invoke-ITSProgram -ProgramPath "programs/lib_tz_ez/run.py" -ProgramArgs $args
