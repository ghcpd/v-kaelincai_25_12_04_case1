#!/usr/bin/env bash
# Run legacy test suite from issue_project and v2 tests, then produce a compare report
ROOT=$(pwd)
LEGACY_DIR="c:\\c\\chatWorkspace\\issue_project"
V2_DIR="$ROOT"

# Run legacy tests
echo "Running legacy tests..."
cd "$LEGACY_DIR"
python -m pytest -q --maxfail=1 || true
legacy_status=$?

# Run v2 tests
echo "Running v2 tests..."
cd "$V2_DIR"
export PYTHONPATH="$V2_DIR"
pytest -q || true
v2_status=$?

# Produce a minimal compare report
python - <<'PY'
import json, sys, pathlib
root = pathlib.Path('$V2_DIR')
legacy = {'status': 'unknown'}
try:
    # TODO: read legacy results if available
    pass
except Exception:
    pass
v2_results = {}
try:
    v2_results = json.loads((root / 'results' / 'results_post.json').read_text())
except Exception:
    v2_results = {'error': 'no results'}
report = root / 'compare_report.md'
report.write_text('# Compare Report\n\n' + json.dumps({'legacy': legacy, 'v2': v2_results}, indent=2))
print('Wrote', report)
PY
