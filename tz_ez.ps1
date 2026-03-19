cd $PSScriptRoot
git pull -q
try {
    .venv/Scripts/Activate.ps1
} catch {
    .venv/bin/Activate.ps1
}
pip install -q -r requirements.txt
python3 lib_tz_ez/run.py @args