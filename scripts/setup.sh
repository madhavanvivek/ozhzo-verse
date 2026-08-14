#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo "Initializing Ozhzo Verse Monorepo Setup"
echo "========================================="

# 1. Environment files
if [ ! -f ".env" ]; then
    echo "Creating root .env from .env.example..."
    cp .env.example .env
fi

if [ ! -f "services/api/.env" ]; then
    echo "Creating services/api/.env from .env.example..."
    cp .env.example services/api/.env
fi

if [ ! -f "apps/web/.env.local" ]; then
    echo "Creating apps/web/.env.local from .env.example..."
    cp .env.example apps/web/.env.local
fi

echo "Environment template files generated."
echo "Setup complete! Run 'docker-compose -f infrastructure/docker/docker-compose.yml up' to launch."
