#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
receipt="${TMPDIR:-/tmp}/bidveil-demo-receipt.json"
rm -f "$receipt"
PYTHONPATH=. python -m bidveil.cli prove fixtures/opportunity.json fixtures/private-profile.json --at 2026-09-13T12:00:00Z --out "$receipt"
PYTHONPATH=. python -m bidveil.cli verify-integrity "$receipt"
PYTHONPATH=. python -m bidveil.cli verify-replay fixtures/opportunity.json fixtures/private-profile.json "$receipt" --at 2026-09-13T12:00:00Z
python - "$receipt" <<'PY'
import json, sys
r=json.load(open(sys.argv[1], encoding='utf-8'))
print(json.dumps({
  'decision': r['decision'],
  'mode': r['mode'],
  'revealed_results': r['revealed_results'],
  'private_values_revealed': r['private_values_revealed'],
  'onchain_proof_verified': r['onchain_proof_verified'],
  'receipt_sha256': r['receipt_sha256'],
}, indent=2, sort_keys=True))
PY
