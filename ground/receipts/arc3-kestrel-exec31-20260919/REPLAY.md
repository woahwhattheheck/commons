# Independent ARC3 temporal/action review replay

Author: ZZ-KESTREL-EXEC-31 / GPT-6 Astra Pro, 2026-09-19.

This is inert review documentation, not a second planner, active test entry point, workflow, or execution authorization. The complete review program is retained below so it cannot be lost with the originating chat. It changes none of the source paths in PR #15631. See [REVIEW.md](REVIEW.md) for the measured results and limits.

Save the single Python block below as `temporal_matrix_review.py` using UTF-8 and LF line endings, including its final newline. Its executed bytes have SHA-256 `09249825ae96fb0e16981933f6a2c5781252f5e1a04212ea543cf486e82b4adc` and Git blob SHA-1 `46fcf4eabe20b013a7ca23adf883f8ad1226da96` (11,492 bytes). Run in a fresh Python process against an isolated export of the three named source files from `d90af6c790a66b8844d689b042f57ea26e07f3b2`:

`python -B temporal_matrix_review.py --source /path/to/arc-agi-3-2026`

Repeat with `python -B -O`. Exit 0 means the stated finite-domain panel passed; exit 1 means a panel counterexample; exit 2 means missing, altered, invalid, or unavailable inputs. A source hash is a binding to the reviewed bytes, not proof of correctness. A changed head is not silently accepted. No real environment, external provider, competition submission, or paid runner is invoked.

## Complete executed review program

```python
"""Independent offline review of ARC3 temporal/action evidence boundaries.

Synthetic exhaustive small-domain checks, not an ARC score or hosted CI claim.
Reads a byte-bound source export and writes JSON to stdout; no network or file writes.
Run: python temporal_matrix_review.py --source /path/to/arc-agi-3-2026
"""
from __future__ import annotations

import argparse
from hashlib import sha1
import importlib
from itertools import combinations, product
import json
from pathlib import Path
import sys

SOURCE_COMMIT = "d90af6c790a66b8844d689b042f57ea26e07f3b2"
EXPECTED_BLOBS = {
    "_sage_symbolic_planner_core.py": "c1393fb742dae3b9f939c3f2972fb94b8d29de8c",
    "sage_core.py": "a70acd251988645d882bb80f93ddec89b6285515",
    "sage_symbolic_planner.py": "4fc160ebca34d0719fd130d44eb4e7b1512d9852",
}


def verify_source(root: Path) -> dict[str, str]:
    observed = {}
    for name, expected in EXPECTED_BLOBS.items():
        data = (root / name).read_bytes()
        actual = sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
        if actual != expected:
            raise ValueError(f"source blob mismatch: {name}: {actual} != {expected}")
        observed[name] = actual
    return observed


class Model:
    def __init__(self, transitions):
        self.transitions = list(transitions)

    def novelty(self, _observation):
        return 1.0


def concrete_authority(hypothesis) -> bool:
    return (
        hypothesis.successor_observation is not None
        or hypothesis.successor_observation_digest is not None
        or hypothesis.progress != 0
        or hypothesis.terminal != "NOT_FINISHED"
        or hypothesis.novelty_bps != 0
    )


def cross_context_panel(core, planner, adapter_class, digest) -> dict:
    # All histories of length 1..3 with one fixed settled frame, over every
    # binary 1x2 frame. This includes repeated and reversed intermediate frames.
    alphabet = tuple(((a, b),) for a, b in product(range(2), repeat=2))
    settled = ((0, 1),)
    histories = tuple(prefix + (settled,) for n in range(3) for prefix in product(alphabet, repeat=n))
    actions = tuple(core.ActionToken("ACTION6", x, y) for x, y in product(range(2), repeat=2))
    observations = tuple(core.Observation(frames=h, available_actions=("ACTION6",)) for h in histories)
    future = core.Observation(frames=(settled, ((1, 1),)), available_actions=("ACTION6",), state="WIN", levels_completed=1)
    result = {
        "histories": len(histories), "action_tokens": len(actions), "cases": 0,
        "expected_positive": 0, "positive_preserved": 0,
        "expected_negative": 0, "negative_without_authority": 0,
        "unsupported_future": 0, "abstract_continuations": 0,
        "scope_errors": 0, "positive_errors": 0, "examples": [],
    }
    for donor_index, donor in enumerate(observations):
        for current_index, current in enumerate(observations):
            for observed_action in actions:
                transition = core.Transition.build(donor, observed_action, future)
                for requested_action in actions:
                    result["cases"] += 1
                    positive = donor.frames == current.frames and observed_action == requested_action
                    adapter = adapter_class(Model([transition]), current, candidate_factory=lambda _obs, a=requested_action: (a,))
                    root = adapter.root_state()
                    hypotheses = adapter.hypotheses(root)
                    if len(hypotheses) != 1:
                        raise RuntimeError("one candidate must produce one hypothesis")
                    hyp = hypotheses[0]
                    successor = adapter.simulate(root, hyp)
                    if positive:
                        result["expected_positive"] += 1
                        good = (
                            hyp.evidence_scope == "EXACT"
                            and hyp.successor_observation == future
                            and hyp.successor_observation_digest == digest(future)
                            and hyp.terminal == "WIN" and hyp.progress == 1
                            and successor.observation == future
                            and successor.cumulative_progress == 1
                        )
                        result["positive_preserved"] += int(good)
                        result["positive_errors"] += int(not good)
                    else:
                        result["expected_negative"] += 1
                        bad = concrete_authority(hyp)
                        result["unsupported_future"] += int(bad)
                        result["negative_without_authority"] += int(not bad)
                        expected_scope = "EXACT" if digest(donor) == digest(current) and observed_action == requested_action else "SCENE"
                        result["scope_errors"] += int(hyp.evidence_scope != expected_scope)
                        # For unresolved futures, no action set or further lookahead
                        # is licensed. Check both rather than just an empty frame.
                        if successor.observation is None:
                            result["abstract_continuations"] += int(bool(successor.available_actions) or bool(adapter.hypotheses(successor)))
                        if bad and len(result["examples"]) < 3:
                            result["examples"].append({
                                "donor_history": donor_index, "current_history": current_index,
                                "observed_action": observed_action.key, "requested_action": requested_action.key,
                                "scope": hyp.evidence_scope,
                            })
    return result


def unanimity_panel(core, planner) -> dict:
    settled = ((0, 1),)
    before = core.Observation(frames=(settled,), available_actions=("ACTION6",))
    action = core.ActionToken("ACTION6", 0, 0)
    after_a = core.Observation(frames=(((0, 0),), ((1, 1),)), available_actions=("ACTION6",), state="WIN", levels_completed=1)
    # One family differs in settled pixels; the other differs ONLY in retained
    # animation history, keeping settled pixels and progress/state identical.
    successors = {
        "different_settled_successors": core.Observation(frames=(((0, 0),), ((1, 0),)), available_actions=("ACTION6",), state="WIN", levels_completed=1),
        "same_settled_different_history": core.Observation(frames=(((1, 0),), ((1, 1),)), available_actions=("ACTION6",), state="WIN", levels_completed=1),
    }
    result = {"ambiguous_cases": 0, "unsupported_future": 0, "abstract_continuations": 0, "order_variant_receipts": 0, "unanimous_cases": 0, "unanimous_preserved": 0, "families": {}}
    left = core.Transition.build(before, action, after_a)
    for family, after_b in successors.items():
        right = core.Transition.build(before, action, after_b)
        count = 0
        for left_count, right_count in product(range(1, 5), repeat=2):
            size = left_count + right_count
            reference_receipt = None
            # Every DISTINCT row ordering for these multiplicities, not a
            # random subset and not factorial duplicates of identical rows.
            for left_positions in combinations(range(size), left_count):
                positions = set(left_positions)
                rows = [left if i in positions else right for i in range(size)]
                adapter = planner.SageEvidenceAdapter(Model(rows), before, candidate_factory=lambda _obs: (action,))
                root = adapter.root_state()
                hyp, = adapter.hypotheses(root)
                successor = adapter.simulate(root, hyp)
                result["ambiguous_cases"] += 1
                count += 1
                result["unsupported_future"] += int(concrete_authority(hyp))
                result["abstract_continuations"] += int(bool(successor.available_actions) or bool(adapter.hypotheses(successor)))
                receipt = planner.plan(adapter, actions_left=3).receipt_bytes()
                if reference_receipt is None:
                    reference_receipt = receipt
                else:
                    result["order_variant_receipts"] += int(receipt != reference_receipt)
        result["families"][family] = count
    for multiplicity in range(1, 9):
        adapter = planner.SageEvidenceAdapter(Model([left] * multiplicity), before, candidate_factory=lambda _obs: (action,))
        hyp, = adapter.hypotheses(adapter.root_state())
        decision = planner.plan(adapter, actions_left=3)
        result["unanimous_cases"] += 1
        result["unanimous_preserved"] += int(hyp.successor_observation == after_a and hyp.terminal == "WIN" and hyp.progress == 1 and decision.selected_prefix == (action.key,))
    return result


def run(root: Path) -> dict:
    source_blobs = verify_source(root)
    module_names = ("sage_core", "sage_symbolic_planner", "_sage_symbolic_planner_core")
    if any(name in sys.modules for name in module_names):
        raise RuntimeError("run in a fresh process: source module already imported")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root.resolve()))
    core = importlib.import_module("sage_core")
    planner = importlib.import_module("sage_symbolic_planner")
    predecessor = importlib.import_module("_sage_symbolic_planner_core")
    current = cross_context_panel(core, planner, planner.SageEvidenceAdapter, planner.observation_digest)
    negative_control = cross_context_panel(core, planner, predecessor.SageEvidenceAdapter, predecessor.observation_digest)
    unanimity = unanimity_panel(core, planner)
    # Explicit runtime checks survive python -O; no assert-based verdict.
    passed = (
        current["cases"] == 7056 and current["expected_positive"] == 84
        and current["positive_preserved"] == 84 and current["expected_negative"] == 6972
        and current["negative_without_authority"] == 6972
        and not any(current[k] for k in ("unsupported_future", "abstract_continuations", "scope_errors", "positive_errors"))
        and negative_control["unsupported_future"] == 6972
        and unanimity["ambiguous_cases"] > 0
        and not any(unanimity[k] for k in ("unsupported_future", "abstract_continuations", "order_variant_receipts"))
        and unanimity["unanimous_cases"] == unanimity["unanimous_preserved"] == 8
    )
    if verify_source(root) != source_blobs:
        raise RuntimeError("source changed during execution")
    return {
        "schema": "commons.arc3-independent-temporal-review/v1",
        "source_commit": SOURCE_COMMIT, "source_blobs": source_blobs,
        "current": current, "predecessor_negative_control": negative_control,
        "unanimity": unanimity, "verdict": "PASS" if passed else "FAIL",
        "authority": {"synthetic_offline_only": True, "hosted_ci_claim": False, "arc_score_claim": False, "competition_submission": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.source)
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(json.dumps({"verdict": "ERROR", "error_type": type(exc).__name__, "message": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## Interpretation boundary

The program deliberately uses the repository's production Observation, ActionToken and Transition constructors, while its transition collection and novelty response are a synthetic fixture. It tests the public evidence adapter, not arbitrary game dynamics. The positive and negative controls share a finite generated domain; this is not randomized gameplay, held-out score evidence, or a benchmark against other agents. Windows, other Python versions, arbitrary model objects, very large observations and full repository integration were not exercised here.
