#!/usr/bin/env bash
set -euo pipefail

EXPECTED_GZIP_SHA256='318418c0d673d3566a36f47efd94d89899d0dc5b33d888c2aa587591d69c614c'
EXPECTED_PATCH_ID='fbd98806a52f1160586d09e997207bbe1a2280c8'
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUT=${1:-"$HERE/titan-v3-calibration.patch"}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cat "$HERE"/packet.b64.part-* | base64 -d > "$TMP/packet.patch.gz"
printf '%s  %s\n' "$EXPECTED_GZIP_SHA256" "$TMP/packet.patch.gz" | sha256sum -c -
gzip -dc "$TMP/packet.patch.gz" > "$OUT"
ACTUAL_PATCH_ID=$(git patch-id --stable < "$OUT" | awk '{print $1}')
test "$ACTUAL_PATCH_ID" = "$EXPECTED_PATCH_ID"
printf 'materialized %s\nsha256(gzip)=%s\npatch-id=%s\n' \
  "$OUT" "$EXPECTED_GZIP_SHA256" "$EXPECTED_PATCH_ID"
