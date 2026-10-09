#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Replit's Python packages live in .pythonlibs, not in a virtual environment.
requirements="$(mktemp)"
trap 'rm -f "$requirements"' EXIT
uv export --frozen --no-dev --no-emit-project --format requirements-txt > "$requirements"
# Optional uv flags allow a full reinstall when checking a clean setup.
uv pip sync --python python --prefix .pythonlibs --require-hashes "$@" "$requirements"
python -c "import streamlit, pandas, plotly, fpdf, pypdf, cryptography"

# This app reads CSV files and has no database schema to migrate.
