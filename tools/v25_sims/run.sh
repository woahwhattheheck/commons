#!/usr/bin/env bash
# Usage: run.sh <SEED_START> <SEED_COUNT> <OUTDIR>
# Runs V2 against the full runnable panel, both seats, official engine.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
W="${V25_WORK:-/tmp/v25}"
START="$1"; COUNT="$2"; OUT="$3"
SEEDS=$(python3 -c "print(','.join(str($START+i) for i in range($COUNT)))")
"$W/.venv/bin/python" -B "$ROOT/tools/v25_sims/gauntlet.py" \
  --seeds "$SEEDS" \
  --opponents arlene,apex,kaito_v43,cok_v10,public_bt12,v1_submitted \
  --workers 8 --action-timeout 15.0 --outdir "$OUT"
