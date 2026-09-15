#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workbench import (  # noqa: E402
    LedgerError,
    evaluate_ledger,
    load_strict_json,
    main,
    publish,
)


SCHEMA = "crowdstrike-aoc-manual-ledger-v1"


def attempt(**kwargs):
    base = {
        "attempt_id": "a1",
        "puzzle_id": "basilisk-1",
        "prompt_text": "please solve this puzzle",
        "observed_token_count": 40,
        "outcome": "success",
        "entry_mode": "manual",
        "declared_actions": ["human_paste"],
    }
    base.update(kwargs)
    return base


def ledger(*attempts):
    return {"schema": SCHEMA, "attempts": list(attempts)}


class WorkbenchTests(unittest.TestCase):
    def test_duplicate_json_keys_rejected(self):
        raw = '{"schema":"x","schema":"y"}'
        with self.assertRaises(LedgerError):
            load_strict_json(raw)

    def test_malformed_token_count_rejected(self):
        for bad in (True, 3.5, "12", -1):
            with self.assertRaises(LedgerError):
                evaluate_ledger(ledger(attempt(observed_token_count=bad)))

    def test_prohibited_automation_flag_rejected(self):
        with self.assertRaises(LedgerError):
            evaluate_ledger(
                ledger(attempt(declared_actions=["bot_live_interaction"]))
            )

    def test_prohibited_text_rejected(self):
        with self.assertRaises(LedgerError):
            evaluate_ledger(
                ledger(attempt(notes="used network interception on scoring"))
            )

    def test_frontier_uses_operator_token_counts_only(self):
        result = evaluate_ledger(
            ledger(
                attempt(attempt_id="a", observed_token_count=90, outcome="success"),
                attempt(attempt_id="b", observed_token_count=30, outcome="success"),
                attempt(attempt_id="c", observed_token_count=10, outcome="failure"),
            )
        )
        front = result["frontiers"][0]
        self.assertEqual(front["best_observed_token_count"], 30)
        self.assertEqual(front["best_attempt_ids"], ["b"])
        self.assertEqual(front["successful_count"], 2)
        by_id = {a["attempt_id"]: a for a in result["attempts"]}
        self.assertEqual(by_id["a"]["delta_from_best"], 60)
        self.assertIsNone(by_id["c"]["delta_from_best"])

    def test_duplicate_prompt_detection(self):
        result = evaluate_ledger(
            ledger(
                attempt(attempt_id="x", prompt_text="hello   world"),
                attempt(attempt_id="y", prompt_text="hello world"),
            )
        )
        groups = result["frontiers"][0]["duplicate_prompt_groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["attempt_ids"], ["x", "y"])

    def test_order_invariance_of_receipt(self):
        a = attempt(attempt_id="p1", puzzle_id="p", observed_token_count=11)
        b = attempt(attempt_id="p2", puzzle_id="p", observed_token_count=22)
        r1 = evaluate_ledger(ledger(a, b))
        r2 = evaluate_ledger(ledger(b, a))
        self.assertEqual(r1["receipt"]["receipt_sha256"], r2["receipt"]["receipt_sha256"])
        self.assertEqual(r1["frontiers"], r2["frontiers"])

    def test_receipt_recompute_detects_tamper(self):
        result = evaluate_ledger(ledger(attempt()))
        digest = result["receipt"]["receipt_sha256"]
        from workbench import build_receipt

        tampered = [dict(result["frontiers"][0], best_observed_token_count=1)]
        rebuilt = build_receipt({"attempts": result["attempts"]}, tampered)
        self.assertNotEqual(digest, rebuilt["receipt_sha256"])
        self.assertEqual(result["receipt"]["compliance_kind"], "SELF_ATTESTED_ONLY")
        self.assertFalse(result["receipt"]["eligibility_certificate"])

    def test_distinct_puzzles_have_distinct_frontiers(self):
        result = evaluate_ledger(
            ledger(
                attempt(attempt_id="1", puzzle_id="A", observed_token_count=5),
                attempt(attempt_id="2", puzzle_id="B", observed_token_count=9),
            )
        )
        self.assertEqual([f["puzzle_id"] for f in result["frontiers"]], ["A", "B"])
        self.assertEqual(result["frontiers"][0]["best_observed_token_count"], 5)
        self.assertEqual(result["frontiers"][1]["best_observed_token_count"], 9)

    def test_create_exclusive_publish(self):
        result = evaluate_ledger(ledger(attempt()))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            js = root / "out.json"
            md = root / "out.md"
            publish(result, js, md)
            self.assertTrue(js.exists())
            self.assertIn("SELF_ATTESTED_ONLY", md.read_text(encoding="utf-8"))
            with self.assertRaises(LedgerError):
                publish(result, js, md)

    def test_cli_fixture(self):
        fixture = ROOT / "fixtures" / "sample_ledger.json"
        code = main([str(fixture)])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
