#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
HOST="${OCR_HOST:-127.0.0.1}"
PORT="${OCR_PORT:-8095}"
exec venv/bin/python -m uvicorn app.main:app --host "$HOST" --port "$PORT"
