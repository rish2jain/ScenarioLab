#!/usr/bin/env python3
"""Dump FastAPI OpenAPI schema to stdout (or a file) without serving HTTP.

Usage:
  cd backend && uv run python ../scripts/dump_openapi.py
  cd backend && uv run python ../scripts/dump_openapi.py -o ../frontend/openapi.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump ScenarioLab OpenAPI schema")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write schema JSON to this path (default: stdout)",
    )
    args = parser.parse_args()

    # Ensure backend package is importable when run from repo root or backend/
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from app.main import app  # noqa: WPS433 — intentional late import after sys.path

    schema = app.openapi()
    text = json.dumps(schema, indent=2) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote OpenAPI schema to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
