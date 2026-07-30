#!/usr/bin/env bash
# Generate TypeScript types from FastAPI OpenAPI schema.
# Usage: ./scripts/generate-types.sh
#
# Sources (in order):
#   1. OPENAPI_SCHEMA_PATH — path to a static openapi.json
#   2. BACKEND_URL/openapi.json — if the backend is running (docs enabled)
#   3. scripts/dump_openapi.py — imports FastAPI app and dumps schema (no server)
#
# Prerequisites:
#   - npm install in frontend/ (openapi-typescript)
#   - For fallback dump: uv + backend deps (cd backend && uv sync)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_URL="${BACKEND_URL:-http://localhost:5001}"
FRONTEND_DIR="${ROOT_DIR}/frontend"
OUTPUT_FILE="${FRONTEND_DIR}/src/lib/generated-types.ts"
SCHEMA_TMP="$(mktemp -t scenariolab-openapi.XXXXXX.json)"
trap 'rm -f "$SCHEMA_TMP"' EXIT

fetch_schema() {
  if [[ -n "${OPENAPI_SCHEMA_PATH:-}" ]]; then
    if [[ ! -f "$OPENAPI_SCHEMA_PATH" ]]; then
      echo "ERROR: OPENAPI_SCHEMA_PATH does not exist: $OPENAPI_SCHEMA_PATH" >&2
      return 1
    fi
    echo "Using static schema at ${OPENAPI_SCHEMA_PATH}..."
    cp "$OPENAPI_SCHEMA_PATH" "$SCHEMA_TMP"
    return 0
  fi

  if curl -sf "${BACKEND_URL}/openapi.json" -o "$SCHEMA_TMP" 2>/dev/null; then
    echo "Fetched OpenAPI schema from ${BACKEND_URL}/openapi.json..."
    return 0
  fi

  echo "Backend OpenAPI unavailable at ${BACKEND_URL}; dumping via FastAPI app import..."
  (
    cd "${ROOT_DIR}/backend"
    uv run python "${ROOT_DIR}/scripts/dump_openapi.py" -o "$SCHEMA_TMP"
  )
}

fetch_schema

echo "Generating TypeScript types..."
npx --prefix "$FRONTEND_DIR" openapi-typescript "$SCHEMA_TMP" -o "$OUTPUT_FILE"

echo "Generated types at: ${OUTPUT_FILE}"
echo ""
echo "Note: Import these types alongside your existing types.ts."
echo "Over time, migrate api clients to use generated types for request/response shapes."
