#!/bin/sh
# Overlay L01 bytes onto an extracted 3b4b tree.
# usage: apply_overlay.sh <extract-dir> <flag-name>
set -e
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
DEST=${1:?extract dir}
FLAG=${2:?flag name (canonical_wrapped|land|sheep|day0buy|tranche|leanplant)}
cp -f "$HERE/overlay/l01_mechanics.py" "$DEST/"
cp -f "$HERE/overlay/main.py" "$DEST/"
cp -f "$HERE/overlay/canonical_main.py" "$DEST/"
cp -f "$HERE/tests/test_l01_mechanisms.py" "$DEST/"
cp -f "$HERE/flags/$FLAG/l01_flags.py" "$DEST/"
echo "applied $FLAG -> $DEST"
