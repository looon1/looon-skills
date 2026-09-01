#!/usr/bin/env bash
set -euo pipefail

skill_root="$(cd "$(dirname "$0")" && pwd)"
bootstrap_python="${ILLUSTRATOR_FLOWCHART_BOOTSTRAP_PYTHON:-python3}"
managed_python="${skill_root}/.venv/bin/python"

if [[ ! -x "$managed_python" ]]; then
  "$bootstrap_python" -m venv "${skill_root}/.venv"
fi
"$managed_python" -m pip install --upgrade pip
"$managed_python" -m pip install -r "${skill_root}/requirements.txt"
"$managed_python" "${skill_root}/doctor.py" "$@"
