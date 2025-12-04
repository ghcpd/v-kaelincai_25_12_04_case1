#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
# shellcheck source=/dev/null
if [[ "$(uname -s)" == MINGW* || "$(uname -s)" == CYGWIN* ]]; then
  source .venv/Scripts/activate
else
  source .venv/bin/activate
fi
pip install --upgrade pip
pip install -r requirements.txt
