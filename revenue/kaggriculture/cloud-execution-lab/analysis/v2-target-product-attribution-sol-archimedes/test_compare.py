# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import unittest

import compare


SEEDS = (11, 13)


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
                trace = (arm.lower() + opponent + str(seed) + str(seat)).encode()
                trace_hash = hashlib.sha256(trace).hexdigest() if delta else hashlib.sha256(
                    ("core" + opponent + str(seed) + str(seat)).encode()
                ).hexdigest()
                games.append({
                    "opponent": opponent,
                    "seed": seed,
                    "candidate_seat": seat,
                    "status": "complete",
                    "failure": None,
                    "scores": scores,
                    "trace_sha256": trace_hash,
                })
    return {
        "schema_version": 1,
        "engine_ref": "engine",
        "engine_sha256": {"engine.py": "a" * 64},
        "loader_sha256": "b" * 64,
        "evaluator_sha256": "c" * 64,
        "candidate": {"entry": "candidate.py", "sha256": "d" * 64},
        "opponents": {name: {"sha256": name} for name in compare.EXPECTED_OPPONENTS},
        "seeds": list(SEEDS),
        "agent_rng_seed": 7,
        "limits": {"action_rpc_seconds": 1.0},
        "method": "official",
        "games": games,
    }


def receipt(arm: str, index: int) -> dict:
    return {
        "schema_version": 1,
        "operation": compare.OPERATION,
        "arm": arm,
        "source": {
            "scheduler_git_blob_sha1": compare.EXPECTED_V2_SCHEDULER_BLOB,
            "closure_sha256": "f" * 64,
        },
        "candidate": {
            "changed_files": ["scheduler.py"],
            "closure_sha256": f"{index:064x}",
            "scheduler_git_blob_sha1": f"{index + 100:040x}",
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
            for index, arm in enumerate(("CORE",) + compare.PRODUCT_ARMS, start=1)
        }
        return documents, receipts

    def test_classifies_products_and_keeps_scope_closed(self) -> None:
        documents, receipts = self.fixtures()
        report = compare.build_report(
            documents, receipts, expected_seeds=SEEDS, git_head="1" * 40
        )
        self.assertEqual(report["verdict"], "ATTRIBUTION_COMPLETE")
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
        self.assertEqual(report["conservative_whitelist"]["recommended_expansions"], ["CARROT"])
        self.assertFalse(report["scope"]["promotion_authorized"])

    def test_rejects_incomplete_panel(self) -> None:
        documents, receipts = self.fixtures()
        documents = copy.deepcopy(documents)
        documents["WOOL"]["games"].pop()
        with self.assertRaises(compare.CompareError):
            compare.build_report(
                documents, receipts, expected_seeds=SEEDS, git_head="1" * 40
            )

    def test_rejects_duplicate_candidate_closure(self) -> None:
        documents, receipts = self.fixtures()
        receipts = copy.deepcopy(receipts)
        receipts["WOOL"]["candidate"]["closure_sha256"] = receipts["MILK"]["candidate"]["closure_sha256"]
        with self.assertRaises(compare.CompareError):
            compare.build_report(
                documents, receipts, expected_seeds=SEEDS, git_head="1" * 40
            )


if __name__ == "__main__":
    unittest.main()
