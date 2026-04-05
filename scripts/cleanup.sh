#!/usr/bin/env bash
# cleanup.sh — Fix common performance and build issues
# Usage: ./scripts/cleanup.sh [--full|-f]
#   --full / -f: Also clear node_modules and reinstall

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
BACKEND="$ROOT/backend"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[cleanup]${NC} $1"; }
warn()  { echo -e "${YELLOW}[cleanup]${NC} $1"; }
error() { echo -e "${RED}[cleanup]${NC} $1"; }

# Prefer npm ci when package-lock.json exists (lockfile-respecting); otherwise npm install.
npm_ci_or_install() {
  local dir="$1"
  if [ -f "$dir/package-lock.json" ]; then
    (cd "$dir" && npm ci)
  else
    warn "No package-lock.json in $dir — using npm install"
    (cd "$dir" && npm install)
  fi
}

FULL=false
for arg in "$@"; do
  case "$arg" in
    --full|-f) FULL=true ;;
    -h|--help)
      echo "Usage: ./scripts/cleanup.sh [--full|-f]"
      echo "  --full, -f  Also clear node_modules and reinstall dependencies"
      exit 0
      ;;
    *)
      warn "Unexpected argument: $arg"
      echo "Usage: ./scripts/cleanup.sh [--full|-f]"
      echo "  --full, -f  Also clear node_modules and reinstall dependencies"
      exit 1
      ;;
  esac
done

# 1. Clear Next.js build cache
if [ -d "$FRONTEND/.next" ]; then
  SIZE=$(du -sh "$FRONTEND/.next" 2>/dev/null | cut -f1)
  info "Removing .next/ cache ($SIZE)..."
  rm -rf "$FRONTEND/.next"
else
  info ".next/ cache already clean"
fi

# 2. Clear TypeScript incremental build info (root + project references in subdirs)
if [ -d "$FRONTEND" ]; then
  TSBUILDINFO_COUNT=$(find "$FRONTEND" -type f -name "*.tsbuildinfo" 2>/dev/null | wc -l | tr -d ' ')
  if [ "${TSBUILDINFO_COUNT:-0}" -gt 0 ]; then
    info "Removing .tsbuildinfo files ($TSBUILDINFO_COUNT)..."
    find "$FRONTEND" -type f -name "*.tsbuildinfo" -delete 2>/dev/null || true
  else
    info "No .tsbuildinfo files under frontend"
  fi
fi

# 3. Clear Python bytecode caches
if [ -d "$BACKEND" ]; then
  PYCACHE_COUNT=$(find "$BACKEND" -depth -type d -name __pycache__ 2>/dev/null | wc -l | tr -d ' ')
  if [ "$PYCACHE_COUNT" -gt 0 ]; then
    info "Removing $PYCACHE_COUNT __pycache__ directories..."
    find "$BACKEND" -depth -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
  fi
  PYCO_COUNT=$(find "$BACKEND" \( -name "*.pyc" -o -name "*.pyo" \) 2>/dev/null | wc -l | tr -d ' ')
  if [ "$PYCO_COUNT" -gt 0 ]; then
    info "Removing $PYCO_COUNT .pyc/.pyo files..."
    find "$BACKEND" \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
  fi
else
  info "Backend directory not found, skipping Python bytecode cleanup"
fi

# 4. Clear pytest cache
if [ -d "$BACKEND/.pytest_cache" ]; then
  info "Removing .pytest_cache..."
  rm -rf "$BACKEND/.pytest_cache"
fi

# 5. Clear ruff cache
if [ -d "$BACKEND/.ruff_cache" ]; then
  info "Removing .ruff_cache..."
  rm -rf "$BACKEND/.ruff_cache"
fi

# 6. Full clean: node_modules reinstall
if [ "$FULL" = true ]; then
  warn "Full clean: removing node_modules..."
  rm -rf "$FRONTEND/node_modules"
  rm -rf "$ROOT/node_modules"

  info "Reinstalling frontend dependencies..."
  npm_ci_or_install "$FRONTEND"

  if [ -f "$ROOT/package.json" ]; then
    info "Reinstalling root dependencies..."
    npm_ci_or_install "$ROOT"
  fi
fi

# 7. Health checks
echo ""
info "--- Health checks ---"

# Check disk usage
if [ -d "$FRONTEND/node_modules" ]; then
  FRONTEND_SIZE=$(du -sh "$FRONTEND/node_modules" 2>/dev/null | cut -f1)
else
  FRONTEND_SIZE="N/A"
fi
info "Frontend node_modules: $FRONTEND_SIZE"

# Check for .env
if [ ! -f "$ROOT/.env" ]; then
  warn "No .env file found at project root — copy from .env.example"
fi

# Check Next.js + React compatibility (NEXT_VER / REACT_VER from installed packages)
if command -v node >/dev/null 2>&1; then
  if [ ! -d "$FRONTEND/node_modules" ]; then
    NEXT_VER="unknown"
    REACT_VER="unknown"
    info "Next.js: $NEXT_VER, React: $REACT_VER — versions unknown: $FRONTEND/node_modules is missing (install dependencies, e.g. npm ci or npm install in frontend)."
  else
    NEXT_VER=$(node -e "console.log(require('$FRONTEND/node_modules/next/package.json').version)" 2>/dev/null || echo "unknown")
    REACT_VER=$(node -e "console.log(require('$FRONTEND/node_modules/react/package.json').version)" 2>/dev/null || echo "unknown")
    if [ "$NEXT_VER" = "unknown" ] || [ "$REACT_VER" = "unknown" ]; then
      info "Next.js: $NEXT_VER, React: $REACT_VER — Node.js in PATH but could not read next and/or react from $FRONTEND/node_modules (missing packages or unreadable package.json)."
    else
      info "Next.js: $NEXT_VER, React: $REACT_VER (Node.js in PATH; resolved from $FRONTEND/node_modules)"
    fi
  fi
else
  NEXT_VER="node-not-found"
  REACT_VER="node-not-found"
  info "Node.js not found in PATH"
  info "Next.js: $NEXT_VER, React: $REACT_VER — frontend: $FRONTEND (versions unknown: Node.js not found in PATH — install Node and put it on PATH to resolve versions)"
fi

# Only nudge for supported Next majors we document (15.x / 16.x) with React 18 still installed
if [[ "$NEXT_VER" =~ ^1[56]\. ]] && [[ "$REACT_VER" =~ ^18\. ]]; then
  warn "React 18 works with Next.js 15/16. React 19 unlocks optional React Compiler support "\
"(experimental in Next.js 15): install babel-plugin-react-compiler and set "\
"experimental.reactCompiler: true in next.config to opt in — performance gains are not guaranteed."
fi

echo ""
info "Cleanup complete. Run 'npm run dev' to start fresh."
