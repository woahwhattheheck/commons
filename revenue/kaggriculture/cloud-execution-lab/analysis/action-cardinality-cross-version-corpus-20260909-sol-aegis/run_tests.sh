#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -B -m py_compile verify_corpus.py test_verify_corpus.py
python -B -m unittest -v test_verify_corpus.py
python -B verify_corpus.py
