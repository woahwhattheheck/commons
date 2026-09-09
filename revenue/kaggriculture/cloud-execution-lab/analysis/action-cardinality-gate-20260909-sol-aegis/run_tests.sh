#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m py_compile action_cardinality_gate.py gate_common.py gate_core.py gate_receipt.py test_support.py test_analyze_replay.py test_run_gate.py test_observed_receipt.py test_build_evidence.py
python -m unittest -v test_analyze_replay.py test_run_gate.py test_observed_receipt.py test_build_evidence.py
python action_cardinality_gate.py verify OBSERVED-107140666.json
