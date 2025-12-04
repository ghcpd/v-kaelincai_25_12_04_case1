#!/usr/bin/env bash
# Run integration tests for v2
export PYTHONPATH="$(pwd)"
pytest -q
