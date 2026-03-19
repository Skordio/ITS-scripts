#!/usr/bin/env zsh
set -euo pipefail

# Change to the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

git pull -q

# Activate virtualenv if present (POSIX path)
if [ -f ../.venv/bin/activate ]; then
  # shellcheck source=/dev/null
  source ../.venvunix/bin/activate
fi

pip install -q -r ../requirements.txt

python3 ../lib_drive_dist/run.py "$@"
