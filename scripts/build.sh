#!/usr/bin/env bash
set -euo pipefail

echo "Building Ozhzo Verse Monorepo..."

# TypeScript Workspace build
if command -v npm &> /dev/null; then
    echo "Running npm build..."
    npm run build
fi

echo "Build complete."
