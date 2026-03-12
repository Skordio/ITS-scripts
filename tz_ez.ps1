cd $PSScriptRoot
git pull -q
.venv/Scripts/Activate.ps1
pip install -q -r requirements.txt
python3 tz_ez_lib/run.py