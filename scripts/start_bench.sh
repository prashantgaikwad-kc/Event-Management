#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH="${BENCH:-$ROOT/frappe-bench}"

cd "$BENCH"
pkill -f "honcho.*$BENCH" 2>/dev/null || true
pkill -f "$BENCH.*bench serve" 2>/dev/null || true
fuser -k 11000/tcp 13000/tcp 2>/dev/null || true
sleep 1

exec bench start
