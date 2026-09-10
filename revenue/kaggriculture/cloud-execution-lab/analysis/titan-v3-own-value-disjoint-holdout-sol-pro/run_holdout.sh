#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
: "${EXPECTED_HEAD:?EXPECTED_HEAD is required}"
: "${EXPECTED_PARENT:?EXPECTED_PARENT is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"

HEAD="$(git rev-parse HEAD)"
test "$HEAD" = "$EXPECTED_HEAD"
test "$(git rev-parse HEAD^)" = "$EXPECTED_PARENT"

LAB=revenue/kaggriculture/cloud-execution-lab
KAG=revenue/kaggriculture
OBJECTIVE="$LAB/analysis/titan-v3-own-value-objective-sol-objective"
CARRIER="$LAB/analysis/titan-v3-own-value-archive-carrier-sol-foundry"
PARENT="$LAB/analysis/titan-v3-own-value-bound-panel-sol-closure"
CASE="$LAB/analysis/titan-v3-own-value-disjoint-holdout-sol-pro"
OUT="${1:-$RUNNER_TEMP/titan-v3-own-value-disjoint-holdout}"
SEEDS="1201189346,2053792019,684357706,572159600,1619590821,1748784700,2100322278,1851971276"

case "$OUT" in
  "$RUNNER_TEMP"/*) ;;
  *) echo "output must stay under RUNNER_TEMP" >&2; exit 2 ;;
esac
rm -rf "$OUT"
mkdir -p "$OUT"
export PYTHONPYCACHEPREFIX="$OUT/pycache"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0

cat > "$OUT/EXPECTED-PATHS.txt" <<'EOF'
.github/workflows/titan-v3-own-value-disjoint-holdout-sol-pro.yml
revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-own-value-disjoint-holdout-sol-pro/README.md
revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-own-value-disjoint-holdout-sol-pro/holdout_admission.py
revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-own-value-disjoint-holdout-sol-pro/run_holdout.sh
revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-own-value-disjoint-holdout-sol-pro/test_holdout_admission.py
EOF
git diff --name-only "$EXPECTED_PARENT" "$HEAD" | LC_ALL=C sort > "$OUT/ACTUAL-PATHS.txt"
LC_ALL=C sort -o "$OUT/EXPECTED-PATHS.txt" "$OUT/EXPECTED-PATHS.txt"
diff -u "$OUT/EXPECTED-PATHS.txt" "$OUT/ACTUAL-PATHS.txt"

git diff --exit-code -- .
test -z "$(git status --porcelain)"

verify_blob() {
  local path="$1" expected="$2" actual
  actual="$(git hash-object "$path")"
  printf '%s  %s\n' "$actual" "$path"
  test "$actual" = "$expected"
}

{
  printf 'head %s\nparent %s\n' "$HEAD" "$EXPECTED_PARENT"
  verify_blob "$LAB/runtime/integrated-selected/CURRENT-ARCHIVE.json" 5bd67f93b832b6f35ea6482d35cebdd0d600cbe1
  verify_blob "$LAB/runtime/integrated-selected/CURRENT-SOURCE.json" d80b40e345bcdbacfed9f7f4c8173aeb134fd781
  verify_blob "$OBJECTIVE/own_value_objective.py" 17c49e220de6b8c1c1ba15a95e4707a3d9cd1ea0
  verify_blob "$OBJECTIVE/compare.py" 9a4642211f2fe16da4452aad0a084a1efa85bb31
  verify_blob "$CARRIER/archive_runtime_guard.py" 2fbc4b45d2f0f06f8ccef2665d8d740d73c9e3db
  verify_blob "$CARRIER/archive_carrier.py" 2f5be09c36368732ddf80a84f3a86b36b2ae405e
  verify_blob "$CARRIER/verify_panel_binding.py" 82f0026fd1924ab3987aaf804eba7cc3f56cd87c
  verify_blob "$PARENT/materialize_evaluator.py" 1041c0c2d9099478f21b6ad7082d0527877a5b14
  verify_blob "$PARENT/action_admission.py" 6a1ab9eeeb01fe6937bc0e56d540142f700172a6
  verify_blob "$KAG/cloud-eval/evaluate.py" 077feb2208b6e0c1727835eb4f8089709bf67f3b
  verify_blob "$KAG/cloud-policy-portfolio/vendor/apex/main.py" f2ae8d9b229755235b93e98cd216d59ba0af4d9f
  verify_blob "$KAG/cloud-frontier-policy/vendor/kaito_v43.py" bdd2efccd63cf52a9510035a45250beb95d5d074
  verify_blob "$KAG/cloud-policy-portfolio/revision2/vendor/opponents/cok-v10.py" 738e4555ebb342a93f8214dec1f537afeff4b0d4
  verify_blob "$KAG/cloud-frontier-decision/public-opponent/submission.py" acf5ee793e06a6d5a1f77cc190230fa8c7d2c343
  verify_blob "$LAB/runtime/variants/v1/candidate.py" 8db1262a2d38cc3115d06732383e18e1132ccfba
  verify_blob "$LAB/runtime/variants/v2/candidate.py" 8db1262a2d38cc3115d06732383e18e1132ccfba
} | tee "$OUT/SOURCE-BLOBS.txt"

(
  cd "$CARRIER"
  python -m py_compile archive_runtime_guard.py archive_carrier.py verify_panel_binding.py test_archive_carrier.py
  python -m unittest -v test_archive_carrier.py
) 2>&1 | tee "$OUT/CARRIER-CONTRACTS.txt"

(
  cd "$PARENT"
  python -m py_compile materialize_evaluator.py action_admission.py test_bound_evidence.py
  python -m unittest -v test_bound_evidence.py
) 2>&1 | tee "$OUT/PARENT-ADMISSION-CONTRACTS.txt"

(
  cd "$CASE"
  python -m py_compile holdout_admission.py test_holdout_admission.py
  python -m unittest -v test_holdout_admission.py
) 2>&1 | tee "$OUT/HOLDOUT-CONTRACTS.txt"

(
  cd "$LAB"
  python build_integrated.py --check
) 2>&1 | tee "$OUT/CANONICAL-BUILD-CHECK.txt"

mkdir -p "$OUT/evaluator"
python "$PARENT/materialize_evaluator.py" \
  --source "$KAG/cloud-eval/evaluate.py" \
  --output "$OUT/evaluator/evaluate.py" \
  --receipt "$OUT/EVALUATOR-MATERIALIZATION.json" \
  | tee "$OUT/EVALUATOR-MATERIALIZATION-STDOUT.json"
python -m py_compile "$OUT/evaluator/evaluate.py"

python "$CARRIER/archive_carrier.py" materialize \
  --lab-root "$LAB" \
  --pointer "$LAB/runtime/integrated-selected/CURRENT-ARCHIVE.json" \
  --overlay "$OBJECTIVE/own_value_objective.py" \
  --output "$OUT/carrier" \
  --git-head "$HEAD" \
  | tee "$OUT/MATERIALIZE-STDOUT.json"

python "$CARRIER/archive_carrier.py" probe \
  --entry "$OUT/carrier/control/control_entry.py" \
  --output "$OUT/CONTROL-PROBE.json" \
  > "$OUT/CONTROL-PROBE-STDOUT.json"
python "$CARRIER/archive_carrier.py" probe \
  --entry "$OUT/carrier/candidate/candidate_entry.py" \
  --output "$OUT/CANDIDATE-PROBE.json" \
  > "$OUT/CANDIDATE-PROBE-STDOUT.json"
python "$CARRIER/archive_carrier.py" verify \
  --root "$OUT/carrier" \
  --output "$OUT/PRE-PANEL-VERIFY.json" \
  > "$OUT/PRE-PANEL-VERIFY-STDOUT.json"

git diff --exit-code -- .
test -z "$(git status --porcelain)"

EVALUATOR="$OUT/evaluator/evaluate.py"
COMMON_ARGS=(
  --engine-dir "$LAB/reference/engine"
  --loader "$KAG/20260907-offline-agent/evaluate.py"
  --opponent "apex=$KAG/cloud-policy-portfolio/vendor/apex/main.py::agent"
  --opponent "kaito_v43=$KAG/cloud-frontier-policy/vendor/kaito_v43.py::agent"
  --opponent "cok_v10=$KAG/cloud-policy-portfolio/revision2/vendor/opponents/cok-v10.py::agent"
  --opponent "public_bt12=$KAG/cloud-frontier-decision/public-opponent/submission.py::agent"
  --opponent "v1=$LAB/runtime/variants/v1/candidate.py::agent"
  --opponent "v2=$LAB/runtime/variants/v2/candidate.py::agent"
  --seeds "$SEEDS"
  --rng-seed 20260910
  --action-timeout 1.0
  --startup-timeout 15
  --game-timeout 180
  --episode-steps 720
  --recheck-first
)

python "$EVALUATOR" \
  "${COMMON_ARGS[@]}" \
  --candidate "$OUT/carrier/control/control_entry.py::agent" \
  --output "$OUT/control.json"

python "$EVALUATOR" \
  "${COMMON_ARGS[@]}" \
  --candidate "$OUT/carrier/candidate/candidate_entry.py::agent" \
  --output "$OUT/candidate.json"

python "$CARRIER/verify_panel_binding.py" \
  --receipt "$OUT/carrier/CARRIER-RECEIPT.json" \
  --control "$OUT/control.json" \
  --candidate "$OUT/candidate.json" \
  --output "$OUT/PANEL-BINDING.json" \
  | tee "$OUT/PANEL-BINDING-STDOUT.json"

python "$OBJECTIVE/compare.py" \
  --control "$OUT/control.json" \
  --candidate "$OUT/candidate.json" \
  --head "$HEAD" \
  --output "$OUT/PAIRED-REPORT.json" \
  --markdown "$OUT/PAIRED-REPORT.md" \
  | tee "$OUT/PAIRED-REPORT-STDOUT.json"

python "$CASE/holdout_admission.py" \
  --control "$OUT/control.json" \
  --candidate "$OUT/candidate.json" \
  --paired "$OUT/PAIRED-REPORT.json" \
  --evaluator-receipt "$OUT/EVALUATOR-MATERIALIZATION.json" \
  --output "$OUT/HOLDOUT-ADMISSION.json" \
  --markdown "$OUT/HOLDOUT-ADMISSION.md" \
  | tee "$OUT/HOLDOUT-ADMISSION-STDOUT.json"

python "$CARRIER/archive_carrier.py" verify \
  --root "$OUT/carrier" \
  --output "$OUT/POST-PANEL-VERIFY.json" \
  > "$OUT/POST-PANEL-VERIFY-STDOUT.json"

OUT="$OUT" HEAD="$HEAD" EXPECTED_PARENT="$EXPECTED_PARENT" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

out = Path(os.environ["OUT"])
def load(name: str):
    return json.loads((out / name).read_text(encoding="utf-8"))

admission = load("HOLDOUT-ADMISSION.json")
binding = load("PANEL-BINDING.json")
post = load("POST-PANEL-VERIFY.json")
carrier = load("carrier/CARRIER-RECEIPT.json")
assert admission["operation"] == "titan-v3-own-value-disjoint-holdout-sol-pro-20260910-01"
assert admission["holdout"]["paired_cells_per_arm"] == 96
assert admission["holdout"]["candidate_hypotheses_spent"] == 1
assert admission["holdout"]["development_seed_overlap"] == []
assert len(admission["rows"]) == 96
assert binding["control_games"] == 96
assert binding["candidate_games"] == 96
assert post["canonical_runtime_equal"] is True
assert carrier["canonical_repository_modified"] is False

retained = {}
for name in (
    "SOURCE-BLOBS.txt",
    "EVALUATOR-MATERIALIZATION.json",
    "PANEL-BINDING.json",
    "PAIRED-REPORT.json",
    "HOLDOUT-ADMISSION.json",
    "POST-PANEL-VERIFY.json",
):
    payload = (out / name).read_bytes()
    retained[name] = {
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }

provenance = {
    "schema_version": 1,
    "operation": admission["operation"],
    "git_head": os.environ["HEAD"],
    "exact_parent": os.environ["EXPECTED_PARENT"],
    "archive_sha256": carrier["archive"]["sha256"],
    "source_manifest_sha256": carrier["archive"]["source_manifest_sha256"],
    "holdout": admission["holdout"],
    "verdict": admission["verdict"],
    "gates": admission["gates"],
    "overall": admission["overall"],
    "by_opponent_seat": admission["by_opponent_seat"],
    "canonical_runtime_equal": True,
    "canonical_release_modified": False,
    "promotion_authorized": False,
    "hosted_leaderboard_claim": False,
    "retained": retained,
}
(out / "PROVENANCE.json").write_text(
    json.dumps(provenance, indent=2, sort_keys=True, allow_nan=False) + "\n",
    encoding="utf-8",
)
PY

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  cat "$OUT/HOLDOUT-ADMISSION.md" >> "$GITHUB_STEP_SUMMARY"
  printf '\n' >> "$GITHUB_STEP_SUMMARY"
  cat "$OUT/PAIRED-REPORT.md" >> "$GITHUB_STEP_SUMMARY"
fi

required=(
  EXPECTED-PATHS.txt
  ACTUAL-PATHS.txt
  SOURCE-BLOBS.txt
  CARRIER-CONTRACTS.txt
  PARENT-ADMISSION-CONTRACTS.txt
  HOLDOUT-CONTRACTS.txt
  CANONICAL-BUILD-CHECK.txt
  EVALUATOR-MATERIALIZATION.json
  carrier/CARRIER-RECEIPT.json
  CONTROL-PROBE.json
  CANDIDATE-PROBE.json
  PRE-PANEL-VERIFY.json
  control.json
  candidate.json
  PANEL-BINDING.json
  PAIRED-REPORT.json
  PAIRED-REPORT.md
  HOLDOUT-ADMISSION.json
  HOLDOUT-ADMISSION.md
  POST-PANEL-VERIFY.json
  PROVENANCE.json
)
for path in "${required[@]}"; do
  test -s "$OUT/$path"
done

git diff --exit-code -- .
test -z "$(git status --porcelain)"
printf '%s\n' "$HEAD" > "$OUT/COMPLETE"
