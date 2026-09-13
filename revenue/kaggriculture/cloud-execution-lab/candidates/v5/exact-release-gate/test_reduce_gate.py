import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gate", HERE / "reduce_gate.py")
gate = importlib.util.module_from_spec(spec)
sys.modules["gate"] = gate
spec.loader.exec_module(gate)


def outcome(own, rival, status="SUCCESS", callback=900, fallbacks=0):
    return {"status": status, "own_score": own, "rival_score": rival, "callback_max_ms": callback, "fallback_count": fallbacks}


def cell(lane, i, c_margin=100, b_margin=0, family="fam", seat=0, c_status="SUCCESS", fallbacks=0):
    base = 10000
    return {
        "cell_id": f"{lane}-{i}-p{seat}",
        "lane": lane,
        "fixture_id": f"fixture-{lane}-{i}",
        "opponent": f"opponent-{lane}-{i}",
        "family": family,
        "seat": seat,
        "candidate": outcome(base + c_margin, base, c_status, fallbacks=fallbacks),
        "control": outcome(base + b_margin, base),
    }


def bundle(cells, counts=None):
    if counts is None:
        counts = {lane: sum(c["lane"] == lane for c in cells) for lane in gate.REQUIRED_LANES}
    return {
        "schema_version": gate.SCHEMA,
        "candidate_sha256": gate.CANDIDATE_SHA256,
        "control_sha256": gate.CONTROL_SHA256,
        "engine_sha256": gate.ENGINE_SHA256,
        "required_lane_cell_counts": counts,
        "cells": cells,
    }


def six(delta=100):
    return [cell(lane, 0, delta, 0, family=f"family-{lane}", seat=i % 2) for i, lane in enumerate(sorted(gate.REQUIRED_LANES))]


class ReleaseGateTests(unittest.TestCase):
    def test_machine_pass_still_requires_root_review(self):
        report = gate.evaluate(bundle(six(100)))
        self.assertEqual(report["machine_status"], "PASS")
        self.assertEqual(report["release_status"], "AWAIT_ROOT_REVIEW")
        self.assertEqual(report["overall"]["positive"], 6)
        self.assertEqual(report["overall"]["worst_delta"], 100)

    def test_identity_mismatch_fails_closed(self):
        b = bundle(six())
        b["candidate_sha256"] = "0" * 64
        with self.assertRaisesRegex(gate.GateError, "candidate identity mismatch"):
            gate.evaluate(b)

    def test_missing_lane_cell_fails_closed(self):
        cells = six()
        b = bundle(cells)
        b["required_lane_cell_counts"]["F29"] = 2
        with self.assertRaisesRegex(gate.GateError, "lane coverage mismatch"):
            gate.evaluate(b)

    def test_duplicate_semantic_cell_fails_closed(self):
        cells = six()
        dup = dict(cells[0])
        dup["cell_id"] = "different-id"
        cells.append(dup)
        counts = {lane: sum(c["lane"] == lane for c in cells) for lane in gate.REQUIRED_LANES}
        with self.assertRaisesRegex(gate.GateError, "duplicate semantic cell"):
            gate.evaluate(bundle(cells, counts))

    def test_timeout_or_fallback_holds(self):
        cells = six()
        cells[0]["candidate"]["status"] = "TIMEOUT"
        cells[1]["candidate"]["fallback_count"] = 1
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["machine_status"], "HOLD")
        self.assertIn("nonclean_status_or_fallback", report["machine_failures"])
        self.assertEqual(set(report["dirty_cells"]), {cells[0]["cell_id"], cells[1]["cell_id"]})

    def test_negative_global_mean_holds(self):
        cells = six(10)
        cells[0]["candidate"]["own_score"] -= 100
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["machine_status"], "HOLD")
        self.assertIn("global_mean_not_positive", report["machine_failures"])

    def test_win_to_loss_exceeding_loss_to_win_holds(self):
        cells = six(10)
        cells[0]["control"] = outcome(10020, 10000)
        cells[0]["candidate"] = outcome(9999, 10000)
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["overall"]["win_to_loss"], 1)
        self.assertEqual(report["overall"]["loss_to_win"], 0)
        self.assertIn("loss_to_win_below_win_to_loss", report["machine_failures"])

    def test_family_and_seat_strata_are_reported(self):
        cells = six(100)
        cells[0]["family"] = "shared"
        cells[1]["family"] = "shared"
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["by_family"]["shared"]["n"], 2)
        self.assertIn("0", report["by_seat"])
        self.assertIn("1", report["by_seat"])

    def test_bool_score_rejected(self):
        cells = six()
        cells[0]["candidate"]["own_score"] = True
        with self.assertRaisesRegex(gate.GateError, "built-in integer"):
            gate.evaluate(bundle(cells))

    def test_report_digest_is_deterministic(self):
        b = bundle(six(42))
        self.assertEqual(gate.evaluate(b)["report_sha256"], gate.evaluate(b)["report_sha256"])


if __name__ == "__main__":
    unittest.main()
