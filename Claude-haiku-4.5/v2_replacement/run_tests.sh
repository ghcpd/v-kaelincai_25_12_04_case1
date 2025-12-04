#!/bin/bash
# Run all integration tests and generate report
#
# Usage:
#   ./run_tests.sh [--verbose] [--coverage]
#
# On Windows (PowerShell):
#   .\run_tests.ps1

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
LOGS_DIR="$SCRIPT_DIR/logs"

mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

echo "========================================================================="
echo "  Running Integration Tests (v2 Routing System)"
echo "========================================================================="
echo ""

# Parse arguments
VERBOSE=""
COVERAGE=""
if [[ "$1" == "--verbose" ]]; then
    VERBOSE="-v"
fi
if [[ "$2" == "--coverage" ]]; then
    COVERAGE="--cov=src/routing_v2"
fi

# Run tests
echo "Running pytest..."
pytest tests/ \
    --pythonpath=src \
    -v \
    --tb=short \
    --junit-xml="$RESULTS_DIR/junit.xml" \
    --log-file="$LOGS_DIR/test_run.log" \
    $COVERAGE \
    2>&1 | tee "$RESULTS_DIR/test_output.txt"

TEST_EXIT_CODE=$?

# Generate summary
echo ""
echo "========================================================================="
echo "  Test Summary"
echo "========================================================================="
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ ALL TESTS PASSED"
else
    echo "✗ SOME TESTS FAILED (exit code: $TEST_EXIT_CODE)"
fi

echo ""
echo "Artifacts:"
echo "  Logs:      $LOGS_DIR/test_run.log"
echo "  Results:   $RESULTS_DIR/"
echo "  Output:    $RESULTS_DIR/test_output.txt"
echo ""

exit $TEST_EXIT_CODE
