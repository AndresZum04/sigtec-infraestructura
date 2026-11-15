#!/usr/bin/env bash
# Entrada única del proyecto integrado Andrés + Kay.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
PYTHON=${SIGTEC_PYTHON:-python3}
exec "$PYTHON" "$ROOT/scripts/sistema.py" "$@"
