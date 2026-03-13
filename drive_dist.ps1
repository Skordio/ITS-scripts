cd $PSScriptRoot
git pull -q
.venv/Scripts/Activate.ps1
pip install -q -r requirements.txt
python3 lib_drive_dist/run.py @args