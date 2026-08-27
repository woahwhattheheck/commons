#!/bin/sh
# Thin debug-APK recipe for the existing lda/ Kotlin app.
# Does not rewrite lda/README.md. Does not remint PR 3812's android/ tree.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
APK="$ROOT/lda/app/build/outputs/apk/debug/app-debug.apk"
cd "$ROOT/lda"
if [ -x ./gradlew ]; then
  ./gradlew assembleDebug
elif command -v gradle >/dev/null 2>&1; then
  gradle assembleDebug
else
  echo "PAY-ADJACENT HOLE: no Gradle wrapper in lda/ and no gradle on PATH."
  echo "Expected output: $APK"
  echo "Build the existing lda/ app, then titan_hands target=wireless act type=serve_apk."
  exit 2
fi
if [ -f "$APK" ]; then
  echo "$APK"
else
  echo "assemble finished but $APK is missing"
  exit 3
fi
