#!/usr/bin/env bash
# Generate TypeScript types from FastAPI OpenAPI schema.
# Usage: ./scripts/generate-types.sh
#
# Prerequisites:
#   - Backend must be running at localhost:5001
#   - npm install -D openapi-typescript (in frontend/)

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:5001}"
FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
OUTPUT_FILE="${FRONTEND_DIR}/src/lib/generated-types.ts"

echo "Fetching OpenAPI schema from ${BACKEND_URL}/openapi.json..."
SCHEMA=$(curl -sf "${BACKEND_URL}/openapi.json") || {
  echo "ERROR: Could not fetch OpenAPI schema. Is the backend running?"
  exit 1
}

echo "Generating TypeScript types..."
echo "$SCHEMA" | npx --prefix "$FRONTEND_DIR" openapi-typescript /dev/stdin -o "$OUTPUT_FILE"

echo "Generated types at: ${OUTPUT_FILE}"
echo ""
echo "Note: Import these types alongside your existing types.ts."
echo "Over time, migrate api.ts to use generated types for request/response shapes."
