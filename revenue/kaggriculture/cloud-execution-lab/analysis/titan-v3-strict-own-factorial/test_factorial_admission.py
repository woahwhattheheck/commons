from __future__ import annotations

import hashlib
import unittest

from factorial_admission import analyze


def trace(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def rows(*, harmful_interaction: bool = False):
    output = []
    for opponent in ("Arlene", "V1"):
        for seat in (0, 1):
            for seed in (11, 22):
                base = 100 + seat
                values = {
                    "incumbent": (base, 80, "win", trace(f"base-{opponent}-{seat}-{seed}")),
                    "strict-only": (base + 4, 80, "win", trace(f"strict-{opponent}-{seat}-{seed}")),
                    "own-only": (base + 6, 80, "win", trace(f"own-{opponent}-{seat}-{seed}")),
                    "combined": (
                        base - 2 if harmful_interaction else base + 12,
                        80,
                        "loss" if harmful_interaction else "win",
                        trace(f"combined-{opponent}-{seat}-{seed}"),
                    ),
                }
                for arm, (own, rival, outcome, digest) in values.items():
                    output.append(
                        {
                            "arm": arm,
                            "opponent": opponent,
                            "seat": seat,
                            "seed": seed,
                            "own_cash": own,
                            "rival_cash": rival,
                            "outcome": outcome,
                            "candidate_action_trace_sha256": digest,
                        }
                    )
    return output


class FactorialAdmissionTests(unittest.TestCase):
    def test_positive_main_effects_and_interaction_admit(self):
        report = analyze(rows())
        self.assertEqual(report["verdict"], "ADMIT")
        self.assertEqual(report["cells"], 8)
        self.assertGreater(report["aggregate"]["own_cash"]["interaction"]["mean"], 0)
        self.assertFalse(report["promotion_authorized"])

    def test_harmful_interaction_rejects(self):
        report = analyze(rows(harmful_interaction=True))
        self.assertEqual(report["verdict"], "REJECT")
        self.assertEqual(report["new_losses"], 8)
        self.assertTrue(any("new losses" in reason for reason in report["reasons"]))

    def test_incomplete_grid_fails_closed(self):
        ledger = rows()
        ledger.pop()
        with self.assertRaisesRegex(ValueError, "incomplete factorial cell"):
            analyze(ledger)

    def test_duplicate_row_fails_closed(self):
        ledger = rows()
        ledger.append(dict(ledger[0]))
        with self.assertRaisesRegex(ValueError, "duplicate arm"):
            analyze(ledger)

    def test_non_hex_trace_fails_closed(self):
        ledger = rows()
        ledger[0]["candidate_action_trace_sha256"] = "z" * 64
        with self.assertRaisesRegex(ValueError, "hex digest"):
            analyze(ledger)


if __name__ == "__main__":
    unittest.main(verbosity=2)
