#!/usr/bin/env bash
set -e
START=$(date +%s%3N)
pytest -q || true
END=$(date +%s%3N)
ELAPSED=$((END-START))
cat > results/results_post.json <<EOF
{
  "tests_run": "see pytest output",
  "elapsed_ms": ${ELAPSED}
}
EOF
echo "Wrote results/results_post.json"
