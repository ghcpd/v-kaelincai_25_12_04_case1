#!/usr/bin/env bash
set -e
python -m pytest -q --durations=10
python scripts/generate_results.py
