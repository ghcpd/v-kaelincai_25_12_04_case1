#!/usr/bin/env bash
set -euo pipefail

echo "Running legacy tests (pre-change)"
cd ../issue_project
python -m pytest -q --disable-warnings --maxfail=0 > ../oswe-mini-secondary/results/results_pre.txt 2>&1 || true

echo "Running prototype tests (post-change)"
cd ../oswe-mini-secondary
python -m pytest -q --disable-warnings --maxfail=0 > results/results_post.txt 2>&1 || true

echo "Parsing results"
python scripts/parse_results.py

echo "Done. See results/"
