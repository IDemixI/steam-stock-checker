#!/usr/bin/env bash
#
# Steam hardware stock checker (standalone shell wrapper)
# Runs check-stock.py from the same directory
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/check-stock.py"
