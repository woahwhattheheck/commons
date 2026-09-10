#!/bin/bash
# Paired-gate panel for PR #12042: base vs head, identical seeds, both seats.
# Arm A (baseline): candidate=base vs champion=base
# Arm B (candidate): candidate=head vs champion=base
EVAL=/home/hatch/build/wt12042-head/revenue/kaggriculture/cloud-execution-lab/reference/evaluator/evaluate.py
ENGINE=/home/hatch/build/wt12042-head/revenue/kaggriculture/cloud-execution-lab/reference/engine
LOADER=/home/hatch/build/commons-12042/revenue/kaggriculture/20260907-offline-agent/evaluate.py
BASE=/tmp/shim12042/base_agent.py::agent
HEAD=/tmp/shim12042/head_agent.py::agent
SEEDS=107130860,2611061001,2611061002,2611061003,2611061004,2611061005,2611061006,2611061007,2611061008,2611061009,2611061010,20260910
OUT=${1:-/tmp/panel12042}
mkdir -p $OUT
run_arm() {
  local name=$1 cand=$2
  python3 $EVAL --engine-dir $ENGINE --loader $LOADER \
    --candidate "$cand" --opponent champion=$BASE \
    --seeds $SEEDS --rng-seed 20260907 \
    --output $OUT/arm-$name.json > $OUT/arm-$name.log 2>&1
  echo "arm-$name exit=$?"
}
run_arm baseline $BASE &
run_arm candidate $HEAD &
wait
echo ALL ARMS DONE
