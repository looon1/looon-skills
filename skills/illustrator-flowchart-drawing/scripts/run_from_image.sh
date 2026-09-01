#!/usr/bin/env bash
set -euo pipefail

skill_root="$(cd "$(dirname "$0")/.." && pwd)"
managed_python="${ILLUSTRATOR_FLOWCHART_PYTHON:-${skill_root}/.venv/bin/python}"
if [[ ! -x "$managed_python" ]]; then
  echo "ILLUSTRATOR_FLOWCHART_ENV_MISSING|Run the package setup script before first use: ./setup.sh --verify-server" >&2
  exit 1
fi
exec "$managed_python" "${skill_root}/scripts/run_from_image.py" "$@"
