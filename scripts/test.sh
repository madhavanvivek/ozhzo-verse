#!/usr/bin/env bash
set -euo pipefail

echo "Running Ozhzo Verse Test Suites..."

# Backend Pytest
if command -v pytest &> /dev/null; then
    echo "Running backend pytest..."
    (cd services/api && pytest -v)
elif [ -d "services/api/.venv" ]; then
    (cd services/api && source .venv/bin/activate && pytest -v)
fi

# Web / TS tests
if command -v npm &> /dev/null; then
    echo "Running npm tests..."
    npm test --if-present
fi

echo "All tests executed."
