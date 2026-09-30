# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

import compare


SEEDS = (11, 13)


def trace_for(label: str, opponent: str, seed: int, seat: int) -> str:
    return hashlib.sha256(f"{label}:{opponent}:{seed}:{seat}".encode()).hexdigest()


def document(arm: str, deltas: dict[str, float] | None = None) -> dict:
    deltas = deltas or {}
    games = []
    for opponent in compare.EXPECTED_OPPONENTS:
        for seed in SEEDS:
            for seat in (0, 1):
                delta = float(deltas.get(opponent, 0.0))
                own = 100.0 + delta
                rival = 90.0
                scores = [rival, rival]
                scores[seat] = own
                final_bank = list(scores)
                trace = trace_for(
                    arm if delta else "CORE", opponent, seed, seat
                )
                games.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "status": "complete",
                        "failure": None,
                        "scores": scores,
                        "steps": 719,
                        "episode_steps": 720,
                        "daily_bank": [
                            {"step": 23, "bank": [10.0, 10.0]},
                            {"step": 718, "bank": final_bank},
                        ],
                        "trace_sha256": trace,
                    }
                )
    return {
        "schema_version": 1,
        "engine_ref": compare.ENGINE_REF,
        "engine_sha256": {"engine.py": "a" * 64},
        "loader_sha256": "b" * 64,
        "evaluator_sha256": "c" * 64,
        "candidate": {
            "entry": "candidate.py",
            "callable": "agent",
            "sha256": compare.V2_ENTRY_SHA256,
        },
        "opponents": {
            name: {
                "entry": f"{name}.py",
                "callable": "agent",
                "sha256": hashlib.sha256(name.encode()).hexdigest(),
            }
            for name in compare.EXPECTED_OPPONENTS
        },
        "seeds": list(SEEDS),
        "agent_rng_seed": 7,
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 15.0,
            "game_seconds_between_steps": 180.0,
        },
        "method": "official",
        "python": "3.11.test",
        "platform": "linux",
        "games": games,
    }


def receipt(arm: str, index: int) -> dict:
    control = arm == "CONTROL"
    return {
        "schema_version": 1,
        "operation": compare.OPERATION,
        "arm": arm,
        "product_arms": list(compare.PRODUCT_ARMS),
        "source": {
            "scheduler_git_blob_sha1": compare.EXPECTED_V2_SCHEDULER_BLOB,
            "closure_sha256": "f" * 64,
            "files": 12,
        },
        "candidate": {
            "changed_files": [] if control else ["scheduler.py"],
            "closure_sha256": "f" * 64 if control else f"{index:064x}",
            "scheduler_git_blob_sha1": (
                compare.EXPECTED_V2_SCHEDULER_BLOB
                if control
                else f"{index + 100:040x}"
            ),
            "old_occurrences_before": 1,
            "old_occurrences_after": 1 if control else 0,
            "core_occurrences_before": 0,
            "core_occurrences_after": 0 if control else 1,
        },
    }


class CompareTests(unittest.TestCase):
    def fixtures(self):
        documents = {
            "CONTROL": document("CONTROL", {"arlene": -5, "v1": -5}),
            "CORE": document("CORE"),
        }
        for arm in compare.PRODUCT_ARMS:
            if arm == "CARROT":
                documents[arm] = document(arm, {"arlene": 5, "v1": 5})
            elif arm == "TOMATO":
                documents[arm] = document(arm, {"arlene": -3, "v1": -3})
            elif arm == "STRAWBERRY":
                documents[arm] = document(arm, {"arlene": 4, "v1": -4})
            else:
                documents[arm] = document(arm)
        receipts = {
            arm: receipt(arm, index)
            for index, arm in enumerate(compare.RECEIPT_ARMS, start=1)
        }
        return documents, receipts

    def build(self, documents, receipts):
        return compare.build_report(
            documents,
            receipts,
            expected_seeds=SEEDS,
            git_head="1" * 40,
        )

    def test_classifies_products_and_keeps_scope_closed(self) -> None:
        documents, receipts = self.fixtures()
        report = self.build(documents, receipts)
        self.assertEqual(report["verdict"], "ATTRIBUTION_COMPLETE")
        self.assertEqual(
            report["control_all_shed_vs_core"]["classification"],
            "MARGINAL_DOWNSIDE",
        )
        self.assertEqual(
            report["products_vs_core"]["CARROT"]["classification"],
            "MARGINAL_UPSIDE",
        )
        self.assertEqual(
            report["products_vs_core"]["TOMATO"]["classification"],
            "MARGINAL_DOWNSIDE",
        )
        self.assertEqual(
            report["products_vs_core"]["STRAWBERRY"]["classification"],
            "MIXED",
        )
        self.assertEqual(
            report["products_vs_core"]["MELON"]["classification"],
            "NO_EFFECT",
        )
        self.assertEqual(
            report["conservative_whitelist"]["recommended_expansions"],
            ["CARROT"],
        )
        self.assertFalse(report["scope"]["promotion_authorized"])
        self.assertEqual(
            report["products_vs_core"]["CARROT"]["by_seat"]["0"]["own_delta"]["mean"],
            5.0,
        )

    def test_rejects_incomplete_panel(self) -> None:
        documents, receipts = self.fixtures()
        documents = copy.deepcopy(documents)
        documents["WOOL"]["games"].pop()
        with self.assertRaises(compare.CompareError):
            self.build(documents, receipts)

    def test_rejects_duplicate_candidate_closure(self) -> None:
        documents, receipts = self.fixtures()
        receipts = copy.deepcopy(receipts)
        receipts["WOOL"]["candidate"]["closure_sha256"] = receipts["MILK"]["candidate"]["closure_sha256"]
        with self.assertRaises(compare.CompareError):
            self.build(documents, receipts)

    def test_rejects_candidate_entry_drift(self) -> None:
        documents, receipts = self.fixtures()
        documents = copy.deepcopy(documents)
        documents["EGG"]["candidate"]["sha256"] = "0" * 64
        with self.assertRaises(compare.CompareError):
            self.build(documents, receipts)

    def test_rejects_string_seed_and_incomplete_steps(self) -> None:
        documents, receipts = self.fixtures()
        documents = copy.deepcopy(documents)
        documents["MILK"]["games"][0]["seed"] = str(SEEDS[0])
        with self.assertRaises(compare.CompareError):
            self.build(documents, receipts)

        documents, receipts = self.fixtures()
        documents["MILK"]["games"][0]["steps"] = 718
        with self.assertRaises(compare.CompareError):
            self.build(documents, receipts)

    def test_rejects_missing_terminal_bank_checkpoint(self) -> None:
        documents, receipts = self.fixtures()
        documents = copy.deepcopy(documents)
        documents["CORE"]["games"][0]["daily_bank"][-1]["step"] = 717
        with self.assertRaises(compare.CompareError):
            self.build(documents, receipts)

    def test_rejects_score_change_without_trace_change(self) -> None:
        documents, receipts = self.fixtures()
        documents = copy.deepcopy(documents)
        documents["CARROT"]["games"][0]["trace_sha256"] = documents["CORE"]["games"][0]["trace_sha256"]
        with self.assertRaises(compare.CompareError):
            self.build(documents, receipts)

    def test_strict_json_rejects_duplicate_keys_and_nan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text('{"x": 1, "x": 2}', encoding="utf-8")
            with self.assertRaises(compare.CompareError):
                compare.strict_object(path)
            path.write_text('{"x": NaN}', encoding="utf-8")
            with self.assertRaises(compare.CompareError):
                compare.strict_object(path)


if __name__ == "__main__":
    unittest.main()
