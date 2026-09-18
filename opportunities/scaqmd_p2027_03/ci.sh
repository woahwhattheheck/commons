#!/usr/bin/env bash
set -euo pipefail
python -m py_compile opportunities/scaqmd_p2027_03/*.py
python -m unittest -v opportunities.scaqmd_p2027_03.test_engine opportunities.scaqmd_p2027_03.test_cli
python -O -m unittest -v opportunities.scaqmd_p2027_03.test_engine opportunities.scaqmd_p2027_03.test_cli
