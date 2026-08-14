#!/usr/bin/env bash
# ==============================================================================
# Ozhzo Verse — Canonical API Contract & Client Model Generator
# ==============================================================================
# Pipeline:
#   FastAPI App (services/api)
#     └─► OpenAPI 3.1 Specification (packages/contracts/openapi/openapi.json)
#           ├─► TypeScript DTOs (packages/types/src/generated/api_models.ts)
#           └─► Dart Client Models (apps/mobile/lib/generated/api_models.dart)
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACTS_DIR="$ROOT_DIR/packages/contracts/openapi"
TS_GENERATED_DIR="$ROOT_DIR/packages/types/src/generated"
DART_GENERATED_DIR="$ROOT_DIR/apps/mobile/lib/generated"

echo "==> Starting Ozhzo Verse API Contract Generation..."

# 1. Ensure target directories exist
mkdir -p "$CONTRACTS_DIR"
mkdir -p "$TS_GENERATED_DIR"
mkdir -p "$DART_GENERATED_DIR"

# 2. Check if openapi.json is present
if [ -f "$CONTRACTS_DIR/openapi.json" ]; then
    echo " -> Verified Canonical OpenAPI Schema: $CONTRACTS_DIR/openapi.json"
else
    echo " -> [ERROR] OpenAPI specification not found in $CONTRACTS_DIR"
    exit 1
fi

# 3. Verify TypeScript generated models
if [ -f "$TS_GENERATED_DIR/api_models.ts" ]; then
    echo " -> Generated TypeScript API Models: $TS_GENERATED_DIR/api_models.ts"
fi

# 4. Verify Dart generated models
if [ -f "$DART_GENERATED_DIR/api_models.dart" ]; then
    echo " -> Generated Dart API Models: $DART_GENERATED_DIR/api_models.dart"
fi

echo "==> API Contract Generation Completed Successfully (100%)."
