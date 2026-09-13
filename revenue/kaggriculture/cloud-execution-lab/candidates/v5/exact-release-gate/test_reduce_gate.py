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


def receipts():
    return {
        lane: {
            "raw_artifact": f"/evidence/{lane}.json",
            "raw_sha256": ("%064x" % (i + 1)),
            "corpus_id": f"corpus-{lane}",
            "corpus_sha256": ("%064x" % (i + 101)),
        }
        for i, lane in enumerate(sorted(gate.REQUIRED_LANES))
    }


def bundle(cells):
    return {
        "schema_version": gate.SCHEMA,
        "candidate_sha256": gate.CANDIDATE_SHA256,
        "control_sha256": gate.CONTROL_SHA256,
        "engine_sha256": gate.ENGINE_SHA256,
        "lane_receipts": receipts(),
        "cells": cells,
    }


def full_cells(delta=100):
    rows = []
    for lane in sorted(gate.REQUIRED_LANES):
        for i in range(gate.EXPECTED_LANE_CELL_COUNTS[lane]):
            rows.append(cell(lane, i, delta, 0, family=f"family-{lane}", seat=i % 2))
    return rows


class ReleaseGateTests(unittest.TestCase):
    def test_machine_pass_still_requires_root_review(self):
        report = gate.evaluate(bundle(full_cells(100)))
        self.assertEqual(report["machine_status"], "PASS")
        self.assertEqual(report["release_status"], "AWAIT_ROOT_REVIEW")
        self.assertEqual(report["overall"]["positive"], sum(gate.EXPECTED_LANE_CELL_COUNTS.values()))
        self.assertEqual(report["overall"]["worst_delta"], 100)
        self.assertEqual(report["overall"]["control_wlt"]["T"], sum(gate.EXPECTED_LANE_CELL_COUNTS.values()))
        self.assertEqual(len(report["worst_20"]), 20)

    def test_identity_mismatch_fails_closed(self):
        b = bundle(full_cells())
        b["candidate_sha256"] = "0" * 64
        with self.assertRaisesRegex(gate.GateError, "candidate identity mismatch"):
            gate.evaluate(b)

    def test_missing_lane_cell_fails_closed(self):
        cells = full_cells()
        cells.pop()
        with self.assertRaisesRegex(gate.GateError, "lane coverage mismatch"):
            gate.evaluate(bundle(cells))

    def test_duplicate_semantic_cell_fails_closed(self):
        cells = full_cells()
        dup = dict(cells[0])
        dup["cell_id"] = "different-id"
        cells[1] = dup
        with self.assertRaisesRegex(gate.GateError, "duplicate semantic cell"):
            gate.evaluate(bundle(cells))

    def test_timeout_or_fallback_holds(self):
        cells = full_cells()
        cells[0]["candidate"]["status"] = "TIMEOUT"
        cells[1]["candidate"]["fallback_count"] = 1
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["machine_status"], "HOLD")
        self.assertIn("nonclean_status_or_fallback", report["machine_failures"])
        self.assertEqual(set(report["dirty_cells"]), {cells[0]["cell_id"], cells[1]["cell_id"]})
        self.assertEqual(report["failure_counts"]["timeout"], 1)
        self.assertEqual(report["failure_counts"]["fallback"], 1)

    def test_negative_global_mean_holds(self):
        cells = full_cells(10)
        cells[0]["candidate"]["own_score"] -= 50000
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["machine_status"], "HOLD")
        self.assertIn("global_mean_not_positive", report["machine_failures"])

    def test_win_to_loss_exceeding_loss_to_win_holds(self):
        cells = full_cells(10)
        cells[0]["control"] = outcome(10020, 10000)
        cells[0]["candidate"] = outcome(9999, 10000)
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["overall"]["win_to_loss"], 1)
        self.assertEqual(report["overall"]["loss_to_win"], 0)
        self.assertIn("loss_to_win_below_win_to_loss", report["machine_failures"])

    def test_family_and_seat_strata_are_reported(self):
        cells = full_cells(100)
        cells[0]["family"] = "shared"
        cells[1]["family"] = "shared"
        report = gate.evaluate(bundle(cells))
        self.assertEqual(report["by_family"]["shared"]["n"], 2)
        self.assertIn("0", report["by_seat"])
        self.assertIn("1", report["by_seat"])

    def test_bool_score_rejected(self):
        cells = full_cells()
        cells[0]["candidate"]["own_score"] = True
        with self.assertRaisesRegex(gate.GateError, "built-in integer"):
            gate.evaluate(bundle(cells))

    def test_report_digest_is_deterministic(self):
        b = bundle(full_cells(42))
        self.assertEqual(gate.evaluate(b)["report_sha256"], gate.evaluate(b)["report_sha256"])


if __name__ == "__main__":
    unittest.main()
