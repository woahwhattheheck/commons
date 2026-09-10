#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
: "${EXPECTED_HEAD:?EXPECTED_HEAD is required}"
: "${EXPECTED_BASE:?EXPECTED_BASE is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
SEEDS="${SEEDS:-1789070589,1789070591,1789070593,1789070597}"
export SEEDS

OUT="${1:-$RUNNER_TEMP/titan-v3-own-strict-factorial}"
case "$OUT" in
  "$RUNNER_TEMP"/*) ;;
  *) echo "output must stay under RUNNER_TEMP" >&2; exit 2 ;;
esac
rm -rf "$OUT"
mkdir -p "$OUT/evaluator"
export PYTHONPYCACHEPREFIX="$OUT/pycache"

KAG=revenue/kaggriculture
LAB="$KAG/cloud-execution-lab"
CASE="$LAB/analysis/titan-v3-own-strict-factorial-sol-integrator"
WORKFLOW=.github/workflows/titan-v3-own-strict-factorial-sol-integrator.yml
HEAD="$(git rev-parse HEAD)"
BASE="$(git rev-parse HEAD^)"
test "$HEAD" = "$EXPECTED_HEAD"
test "$BASE" = "$EXPECTED_BASE"

git diff --exit-code -- .
test -z "$(git status --porcelain)"

python - "$BASE" "$HEAD" "$CASE" "$WORKFLOW" <<'PY' | tee "$OUT/CHANGE-BOUNDARY.json"
import json
from pathlib import Path
import subprocess
import sys
base, head, case, workflow = sys.argv[1:]
changed = subprocess.check_output(
    ["git", "diff", "--name-only", base, head], text=True
).splitlines()
unexpected = [
    path for path in changed
    if path != workflow and not path.startswith(case + "/")
]
required = {
    workflow,
    case + "/README.md",
    case + "/factorial_admission.py",
    case + "/materialize_evaluator.py",
    case + "/materialize_factorial.py",
    case + "/run_factorial.sh",
    case + "/test_factorial_admission.py",
    case + "/test_materialize_evaluator.py",
    case + "/test_materialize_factorial.py",
}
missing = sorted(required - set(changed))
if unexpected or missing:
    raise SystemExit(
        "factorial commit boundary mismatch: "
        + json.dumps({"unexpected": unexpected, "missing": missing})
    )
print(json.dumps({
    "base": base,
    "head": head,
    "changed": changed,
    "unexpected": unexpected,
    "missing": missing,
}, indent=2, sort_keys=True))
PY

verify_blob() {
  local path="$1" expected="$2" actual
  actual="$(git hash-object "$path")"
  printf '%s  %s\n' "$actual" "$path"
  test "$actual" = "$expected"
}

{
  printf 'head %s\nbase %s\n' "$HEAD" "$BASE"
  verify_blob "$LAB/runtime/integrated-selected/CURRENT-ARCHIVE.json" 5bd67f93b832b6f35ea6482d35cebdd0d600cbe1
  verify_blob "$KAG/cloud-eval/evaluate.py" 077feb2208b6e0c1727835eb4f8089709bf67f3b
  verify_blob "$LAB/reference/titan-current/latest/selected_sell_core.py" f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3
  verify_blob "$KAG/cloud-opponent-league/lark-responsive/pressure_priority.py" 7261674962d10fc8bc6af5ff73ff9212c40f61ad
  verify_blob "$LAB/titan_runtime.py" b952c9c228ecbde592bf3d2df01638677abb0d24
} | tee "$OUT/SOURCE-BLOBS.txt"

(
  cd "$CASE"
  python -m py_compile \
    factorial_admission.py materialize_evaluator.py materialize_factorial.py \
    test_factorial_admission.py test_materialize_evaluator.py \
    test_materialize_factorial.py
  python -m unittest -v \
    test_factorial_admission.py \
    test_materialize_evaluator.py \
    test_materialize_factorial.py
) 2>&1 | tee "$OUT/CONTRACTS.txt"

python "$CASE/materialize_evaluator.py" \
  --source "$KAG/cloud-eval/evaluate.py" \
  --output "$OUT/evaluator/evaluate.py" \
  --receipt "$OUT/EVALUATOR-MATERIALIZATION.json" \
  | tee "$OUT/EVALUATOR-MATERIALIZATION-STDOUT.json"
python -m py_compile "$OUT/evaluator/evaluate.py"

python "$CASE/materialize_factorial.py" \
  --lab-root "$LAB" \
  --output "$OUT/runtime" \
  --receipt "$OUT/FACTORIAL-MATERIALIZATION.json" \
  | tee "$OUT/FACTORIAL-MATERIALIZATION-STDOUT.json"

OUT="$OUT" python - <<'PY'
import json
import os
from pathlib import Path
out = Path(os.environ["OUT"])
receipt = json.loads((out / "FACTORIAL-MATERIALIZATION.json").read_text())
assert receipt["canonical"]["archive_sha256"] == "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
assert receipt["canonical"]["source_manifest_sha256"] == "3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469"
assert receipt["canonical"]["archive_bytes"] == 428158
assert receipt["canonical"]["runtime_files"] == 109
assert set(receipt["arms"]) == {"control", "own_only", "strict_only", "both"}
assert receipt["canonical_repository_modified"] is False
assert receipt["canonical_archive_modified"] is False
assert receipt["promotion_authorized"] is False
for arm in receipt["arms"]:
    entry = out / "runtime" / "arms" / arm / "main.py"
    assert entry.is_file() and entry.stat().st_size > 0
    assert receipt["arms"][arm]["embedded_source_manifest_unmodified"] is True
PY

git diff --exit-code -- .
test -z "$(git status --porcelain)"

EVALUATOR="$OUT/evaluator/evaluate.py"
COMMON_ARGS=(
  --engine-dir "$LAB/reference/engine"
  --loader "$KAG/20260907-offline-agent/evaluate.py"
  --opponent "arlene=$LAB/runtime/variants/v1/reference/next-panel/vendor/arlene.py::agent"
  --opponent "v1=$LAB/runtime/variants/v1/candidate.py::agent"
  --seeds "$SEEDS"
  --rng-seed 20260910
  --action-timeout 1.0
  --startup-timeout 15
  --game-timeout 180
  --recheck-first
)

for arm in control own_only strict_only both; do
  python "$EVALUATOR" \
    "${COMMON_ARGS[@]}" \
    --candidate "$OUT/runtime/arms/$arm/main.py::agent" \
    --output "$OUT/$arm.json" \
    2>&1 | tee "$OUT/$arm.log"
done

python "$CASE/factorial_admission.py" \
  --control "$OUT/control.json" \
  --own-only "$OUT/own_only.json" \
  --strict-only "$OUT/strict_only.json" \
  --both "$OUT/both.json" \
  --output "$OUT/FACTORIAL-ADMISSION.json" \
  --markdown "$OUT/FACTORIAL-ADMISSION.md" \
  | tee "$OUT/FACTORIAL-ADMISSION-STDOUT.json"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat "$OUT/FACTORIAL-ADMISSION.md" >> "$GITHUB_STEP_SUMMARY"
fi

OUT="$OUT" HEAD="$HEAD" BASE="$BASE" CASE="$CASE" SEEDS="$SEEDS" python - <<'PY'
import hashlib
import json
import os
from pathlib import Path
import subprocess

out = Path(os.environ["OUT"])

def load(name):
    return json.loads((out / name).read_text(encoding="utf-8"))

materialization = load("FACTORIAL-MATERIALIZATION.json")
evaluator = load("EVALUATOR-MATERIALIZATION.json")
admission = load("FACTORIAL-ADMISSION.json")
files = {}
for path in sorted(out.rglob("*")):
    if path.is_file() and path.name not in ("PROVENANCE.json", "COMPLETE"):
        data = path.read_bytes()
        files[path.relative_to(out).as_posix()] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

result = {
    "schema_version": 1,
    "operation": "TITAN-V3-OWN-VALUE-X-STRICT-PRESSURE-FACTORIAL-20260910-01",
    "claim": {
        "channel_id": "C0C0Z8AHGP2",
        "message_ts": "1789070588.331379",
    },
    "repository": "woahwhattheheck/commons",
    "git_head": os.environ["HEAD"],
    "base_commit": os.environ["BASE"],
    "run_script_git_blob": subprocess.check_output(
        ["git", "hash-object", f"{os.environ['CASE']}/run_factorial.sh"],
        text=True,
    ).strip(),
    "canonical": materialization["canonical"],
    "factor_sources": materialization["factor_sources"],
    "arms": {
        arm: {
            "tree_sha256": materialization["arms"][arm]["tree"]["sha256"],
            "target_files_after": materialization["arms"][arm]["target_files_after"],
        }
        for arm in ("control", "own_only", "strict_only", "both")
    },
    "evaluator": evaluator,
    "seeds": [int(value) for value in os.environ["SEEDS"].split(",")],
    "opponents": ["arlene", "v1"],
    "both_seats": True,
    "planned_games_per_arm": 16,
    "planned_games_total": 64,
    "admission_verdict": admission["verdict"],
    "gates": admission.get("gates"),
    "contrasts": admission.get("contrasts"),
    "interaction": admission.get("interaction"),
    "screening_panel_only": True,
    "disjoint_holdout_claim": False,
    "canonical_release_modified": False,
    "promotion_authorized": False,
    "hosted_leaderboard_claim": False,
    "kaggle_state_modified": False,
    "files": files,
}
(out / "PROVENANCE.json").write_text(
    json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
    encoding="utf-8",
)
PY

required=(
  CHANGE-BOUNDARY.json
  SOURCE-BLOBS.txt
  CONTRACTS.txt
  EVALUATOR-MATERIALIZATION.json
  evaluator/evaluate.py
  FACTORIAL-MATERIALIZATION.json
  control.json
  own_only.json
  strict_only.json
  both.json
  FACTORIAL-ADMISSION.json
  FACTORIAL-ADMISSION.md
  PROVENANCE.json
)
for path in "${required[@]}"; do
  test -s "$OUT/$path"
done

git diff --exit-code -- .
test -z "$(git status --porcelain)"
printf '%s\n' "$HEAD" > "$OUT/COMPLETE"
python - "$OUT/FACTORIAL-ADMISSION.json" <<'PY'
import json
from pathlib import Path
import sys
report = json.loads(Path(sys.argv[1]).read_text())
print(json.dumps({
    "verdict": report["verdict"],
    "total_games": report["total_games"],
    "promotion_authorized": report["promotion_authorized"],
    "both_vs_control": report["contrasts"]["both_vs_control"]["overall"],
    "interaction": report["interaction"]["overall"],
}, sort_keys=True))
PY
