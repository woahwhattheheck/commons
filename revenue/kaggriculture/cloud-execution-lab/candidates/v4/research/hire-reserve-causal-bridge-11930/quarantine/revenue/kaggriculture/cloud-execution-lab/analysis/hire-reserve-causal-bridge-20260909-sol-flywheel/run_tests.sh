#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -B -m py_compile verify_bridge.py test_verify_bridge.py
python -B -m unittest -v test_verify_bridge.py
python -B verify_bridge.py
