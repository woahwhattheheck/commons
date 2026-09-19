#!/bin/sh
# sample_run.sh -- the demonstrated sample run for a new operator.
#
# Five steps, in the order a new operator should do them the first time.
# Steps 1-2 are deterministic: they use the synthetic fixture and give the same
# answer on any machine, so a failure there is a real failure and not drift.
# Steps 3-5 read the live lane tree, so their numbers move as work lands.
#
# Usage:  sh sample_run.sh [survey-root] [repo-root]
#   survey-root  directory holding the uiowa_rfq_18649_* lanes   (default: ..)
#   repo-root    repository root for a component runner's {REPO} placeholder
#                (default: the parent of survey-root; only needs overriding when
#                 survey-root is an assembled view rather than the real revenue dir)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${1:-$(cd "$HERE/.." && pwd)}
REPO=${2:-$(cd "$ROOT/.." && pwd)}
cd "$HERE"

echo "== 1/5 self-test: does the verifier itself still behave? =="
python3 -m unittest test_verify_kit 2>&1 | tail -3

echo
echo "== 2/5 deterministic demo on the synthetic fixture (known ground truth) =="
echo "   expect: alpha WORKING, bravo DRAFT, charlie DRAFT, delta MISSING, echo UNMAPPED"
python3 verify_kit.py --root fixtures/minikit --manifest fixtures/minikit_manifest.json \
    --timeout 30

echo
echo "== 3/5 real survey of the live lane tree at $ROOT =="
python3 verify_kit.py --root "$ROOT" --repo-root "$REPO" --timeout 90 \
    --out-json sample/component_status.json \
    --out-csv  sample/component_status.csv \
    --out-md   sample/verification_log.md

echo
echo "== 4/5 regenerate the operator guide from that survey =="
python3 render_guide.py --status sample/component_status.json --out OPERATOR_GUIDE.md

echo
echo "== 5/5 where to go next =="
echo "   OPERATOR_GUIDE.md          the six phases, per-phase commands, per-component status"
echo "   sample/component_status.csv one row per component (open in a spreadsheet)"
echo "   sample/verification_log.md  the verbatim output of every command that was run"
echo "   university_inputs.csv       the University inputs still needed; all UNKNOWN"
