#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
exec python -m pytest -v -s tests/verify_faults.py "$@"
