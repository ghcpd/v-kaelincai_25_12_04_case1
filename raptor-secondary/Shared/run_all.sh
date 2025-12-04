#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ISSUE_PROJECT="$ROOT/../issue_project"
RESULTS_DIR="$ROOT/Shared/results"
mkdir -p "$RESULTS_DIR"

# Run legacy tests
cd "$ISSUE_PROJECT"
legacy_log="$RESULTS_DIR/results_pre.log"
echo "Running legacy tests..."
python -m pytest -q | tee "$legacy_log"
legacy_exit=${PIPESTATUS[0]}
python - <<'PY'
import json, sys, pathlib
log_path = pathlib.Path(sys.argv[1])
out = log_path.read_text()
exit_code = int(sys.argv[2])
(pathlib.Path(sys.argv[3])).write_text(json.dumps({"exit_code": exit_code, "output": out}, indent=2))
PY "$legacy_log" "$legacy_exit" "$RESULTS_DIR/results_pre.json"

# Run greenfield tests
cd "$ROOT"
if [[ ! -d .venv ]]; then
  "$ROOT/setup.sh"
fi
"$ROOT/run_tests.sh"
cp "$ROOT/results/results_post.json" "$RESULTS_DIR/results_post.json"
# aggregated_metrics.json already written by pytest hook in Shared/results

echo "Artifacts in $RESULTS_DIR"
