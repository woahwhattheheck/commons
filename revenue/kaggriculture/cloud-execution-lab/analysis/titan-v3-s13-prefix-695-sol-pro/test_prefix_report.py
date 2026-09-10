# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import prefix_report


def report(candidate_values):
    games = []
    for opponent, seed, seat, own, rival, trace in candidate_values:
        scores = [rival, rival]
        scores[seat] = own
        scores[1 - seat] = rival
        games.append({"opponent": opponent, "seed": seed, "candidate_seat": seat, "scores": scores, "status": "complete", "failure": None, "trace_sha256": trace})
    return {"games": games}


class PrefixReportTests(unittest.TestCase):
    def test_strict_survivor_and_retention(self) -> None:
        keys = [("a", 1, 0), ("a", 1, 1), ("v1", 2, 0), ("v1", 2, 1)]
        control = [(o, s, seat, 100, 90, "c") for o, s, seat in keys]
        full = [(o, s, seat, 120, 91, "f") for o, s, seat in keys]
        prefix = [(o, s, seat, 118, 91, "p") for o, s, seat in keys]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = []
            for name, value in (("c", control), ("f", full), ("p", prefix)):
                path = root / f"{name}.json"
                path.write_text(json.dumps(report(value)))
                paths.append(path)
            result = prefix_report.build_report(*paths)
        self.assertEqual(result["verdict"], "PREFIX_SURVIVOR")
        self.assertEqual(result["prefix"]["mean_own_cash_delta"], 18)
        self.assertEqual(result["prefix_vs_full"]["mean_own_cash_delta"], -2)
        self.assertEqual(result["prefix_vs_full"]["retained_mean_own_uplift_fraction"], 0.9)

    def test_new_loss_holds(self) -> None:
        control = [("a", 1, 0, 100, 90, "c")]
        full = [("a", 1, 0, 120, 90, "f")]
        prefix = [("a", 1, 0, 95, 100, "p")]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            paths = []
            for name, value in (("c", control), ("f", full), ("p", prefix)):
                path = root / f"{name}.json"
                path.write_text(json.dumps(report(value)))
                paths.append(path)
            result = prefix_report.build_report(*paths)
        self.assertEqual(result["verdict"], "PREFIX_HOLD")
        self.assertEqual(result["prefix"]["new_losses"], 1)


if __name__ == "__main__":
    unittest.main()
