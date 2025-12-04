#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH=src pytest -q --disable-warnings --maxfail=1
