#!/usr/bin/env bash
set -euo pipefail

echo "Cleaning Ozhzo Verse Monorepo build artifacts and caches..."

rm -rf \
  node_modules \
  apps/*/node_modules \
  packages/*/node_modules \
  apps/*/.next \
  apps/*/dist \
  packages/*/dist \
  services/api/.pytest_cache \
  services/api/.ruff_cache \
  services/api/.mypy_cache \
  services/api/__pycache__ \
  services/api/src/**/__pycache__ \
  .turbo

echo "Workspace clean."
