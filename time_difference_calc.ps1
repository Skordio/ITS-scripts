cd $PSScriptRoot
git pull -q
.venv/Scripts/Activate.ps1
pip install -q -r requirements.txt
python3 time_difference_calc_script.py @args