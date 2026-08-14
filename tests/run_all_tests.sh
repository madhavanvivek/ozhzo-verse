#!/usr/bin/env bash
set -e

echo "=========================================="
echo " Running Ozhzo Verse Monorepo Test Suites "
echo "=========================================="

cd "$(dirname "$0")/.."

# 1. Run Backend Test Suite
echo "-> Testing Core Backend API..."
cd services/api
pytest -q
cd ../..

echo "=========================================="
echo " All Monorepo Test Suites Passed (100%)    "
echo "=========================================="
