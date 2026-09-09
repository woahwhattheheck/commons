#!/usr/bin/env bash
# One-time setup. Idempotent. No arguments.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
W="${V25_WORK:-/tmp/v25}"
mkdir -p "$W"
python3 -m venv "$W/.venv" 2>/dev/null || true
"$W/.venv/bin/pip" install --quiet "kaggle-environments==1.32.7"
ENG=$("$W/.venv/bin/python" -c "import kaggle_environments,os;print(os.path.dirname(kaggle_environments.__file__))")
mkdir -p "$W/engine"
cp "$ENG/envs/kaggriculture/kaggriculture.py" "$ENG/envs/kaggriculture/kaggriculture.json" "$ENG/utils.py" "$W/engine/"
# Verify engine bytes against the pinned official hashes.
cd "$W/engine"
echo "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e  kaggriculture.py
a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867  kaggriculture.json
537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b  utils.py" | sha256sum -c -
# Extract pinned controllers.
E="$ROOT/revenue/kaggriculture/cloud-execution-lab/exports"
echo "6705147ba96fe4c6c3762197f024ff1d47d38004f03d0059055ef4467bb5b88e  $E/titan-current.tar.gz" | sha256sum -c -
mkdir -p "$W/v2" "$W/v1"
tar xzf "$E/titan-current.tar.gz" -C "$W/v2"
tar xzf "$E/historical/titan-7b58fa06da778b1519b81d509d28dff3481b3bbcc7a2d656e8bdfe4a22540524.tar.gz" -C "$W/v1"
echo "SETUP OK  work=$W"
