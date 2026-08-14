#!/usr/bin/env bash
set -euo pipefail

echo "Running Ozhzo Verse Linting & Code Quality Checks..."

# Backend Ruff / Mypy
if command -v ruff &> /dev/null; then
    echo "Running Ruff linter on services/api..."
    (cd services/api && ruff check src/ tests/)
fi

# Frontend ESLint
if command -v npm &> /dev/null; then
    echo "Running npm lint on workspace..."
    npm run lint --if-present
fi

echo "Lint checks complete."
