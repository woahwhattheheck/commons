# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
import tarfile
import unittest

import pruning_ablation as a


def synthetic_source():
    prefix = b"def outer():\n    pass\n\n"
    suffix = (
        b"    elif not reference_feasible:\n"
        b"        marker='forced-feasibility-and-e18-tail'\n"
        b"        return marker\n"
    )
    return prefix + a._PRUNED_BLOCK + suffix


def compile_strict_loop(block: bytes):
    prelude = """def run(candidates, capacity_ok, score_fn):
    quantity=2
    now=0
    minimum_now=0
    end=1
    last=718
    scenarios=[('no_rival',0,'paired'),('rival',1,'paired')]
    baseline=[(10,), (10,)]
    reference_feasible=True
    rule='strict'
    best_plan=((0,2),)
    best_key=(0.0,0.0,0.0)
    best_scores=baseline
    found_feasible=True
    accepted=False
    acceptance_score=0.0
    weighted_expected_gain=0.0
    names=['no_rival','rival']
    weights={'no_rival':0.5,'rival':0.5}
    def _weighted_gain(deltas,names,weights):
        return sum(float(delta)*float(weights[name]) for delta,name in zip(deltas,names))
    class Model:
        def score(self, plan, quantity, rival, alignment, terminal):
            return (score_fn(plan,rival),)
    model=Model()
"""
    source = prelude + block.decode("utf-8") + "    return best_plan,accepted\n"
    namespace = {}
    exec(compile(source, "<strict-loop-witness>", "exec"), namespace)
    return namespace["run"]


class PruningAblationTests(unittest.TestCase):
    def test_exact_block_replacement_and_tail_identity(self):
        raw = synthetic_source()
        changed = a._rewrite_selected_sell_core(raw, a.git_blob_bytes(raw))
        self.assertNotIn(a._PRUNED_BLOCK, changed)
        self.assertEqual(changed.count(a._FULL_EVALUATION_BLOCK), 1)
        marker = b"    elif not reference_feasible:\n"
        self.assertEqual(raw.split(marker, 1)[1], changed.split(marker, 1)[1])

    def test_wrong_source_blob_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "preimage drift"):
            a._rewrite_selected_sell_core(synthetic_source(), "0" * 40)

    def test_missing_or_duplicate_block_fails_closed(self):
        raw = synthetic_source()
        missing = raw.replace(a._PRUNED_BLOCK, b"")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            a._rewrite_selected_sell_core(missing, a.git_blob_bytes(missing))
        duplicate = raw.replace(a._PRUNED_BLOCK, a._PRUNED_BLOCK + a._PRUNED_BLOCK)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            a._rewrite_selected_sell_core(duplicate, a.git_blob_bytes(duplicate))

    def test_prune_changes_callback_and_score_work_but_not_result(self):
        pruned = compile_strict_loop(a._PRUNED_BLOCK)
        full = compile_strict_loop(a._FULL_EVALUATION_BLOCK)
        candidates = [((0,2),), ((0,1),(1,1))]

        def run(fn):
            capacity_calls = []
            score_calls = []
            def capacity(plan):
                capacity_calls.append(plan)
                return True
            def score(plan, rival):
                score_calls.append((plan, rival))
                if plan == ((0,2),):
                    return 10
                return 9 if rival == 0 else 20
            result = fn(candidates, capacity, score)
            return result, capacity_calls, score_calls

        pruned_result, pruned_capacity, pruned_scores = run(pruned)
        full_result, full_capacity, full_scores = run(full)
        self.assertEqual(pruned_result, full_result)
        self.assertLess(len(pruned_capacity), len(full_capacity))
        self.assertLess(len(pruned_scores), len(full_scores))
        self.assertEqual(pruned_capacity, [])
        self.assertEqual(len(full_capacity), 2)

    def test_treatment_block_has_capacity_before_all_scenario_scoring(self):
        block = a._FULL_EVALUATION_BLOCK
        capacity = block.index(b"if capacity_ok and not capacity_ok(plan):continue")
        scoring = block.index(
            b"scores=[model.score(plan,quantity,r,a,end==last) for _,r,a in scenarios]"
        )
        self.assertLess(capacity, scoring)
        self.assertNotIn(b"first_score=", block)
        self.assertNotIn(b"competitive=", block)

    def test_archive_parser_rejects_traversal(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            info = tarfile.TarInfo("../bad")
            payload = b"x"
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        with self.assertRaisesRegex(ValueError, "invalid archive path"):
            a.archive_members_bytes(stream.getvalue())

    def test_treatment_receipt_requires_exact_one_member(self):
        control = {"main.py": b"m", a.TARGET_MEMBER: b"old", "x.py": b"x"}
        treatment = dict(control)
        treatment[a.TARGET_MEMBER] = b"new"
        receipt = a.treatment_receipt(control, treatment)
        self.assertEqual(receipt["changed_members"], [a.TARGET_MEMBER])
        bad = dict(treatment)
        bad["x.py"] = b"changed"
        with self.assertRaisesRegex(ValueError, "one-member"):
            a.treatment_receipt(control, bad)


if __name__ == "__main__":
    unittest.main()
