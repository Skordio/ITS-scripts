. "$PSScriptRoot/script_helper.ps1"

Initialize-ITSRuntime
Invoke-ITSProgram -ProgramPath "programs/time_difference_calc.py" -ProgramArgs $args
