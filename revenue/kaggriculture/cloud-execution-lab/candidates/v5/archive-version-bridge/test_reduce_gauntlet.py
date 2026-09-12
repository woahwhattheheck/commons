import json
from pathlib import Path
import tempfile
import unittest

import reduce_gauntlet as rg


def write_json(path, value):
    Path(path).write_text(json.dumps(value) + "\n", encoding="utf-8")


class ReduceGauntletTests(unittest.TestCase):
    def root(self, base, label, shard=0, shards=1):
        path = Path(base) / f"{label}-{shard}"
        path.mkdir()
        write_json(path / "run.json", {
            "candidate_sha256": rg.EXACT[label],
            "index_sha256": "a" * 64,
            "engine": {"e": "b" * 64},
            "selected_fixtures": 2,
            "group": "all",
            "shard": shard,
            "shards": shards,
        })
        return path

    def game(self, root, label, opponent, seat, scores, family="F", submission=7, status="complete", steps=719):
        write_json(root / f"{opponent}-p{seat}.json", {
            "opponent": opponent,
            "submission_id": submission,
            "family": family,
            "kind": "recorded_trace",
            "adaptive": False,
            "recorded_orientation": seat == 0,
            "memberships": [{"group": "current_top30"}],
            "candidate_sha256": rg.EXACT[label],
            "status": status,
            "scores": scores if status == "complete" else None,
            "steps": steps,
        })

    def test_complete_panel_and_hotspot_ranking(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.root(td, "v31"), self.root(td, "v4")
            for opp, family, sub, v31, v4 in [
                ("oppA", "A", 1, ([110, 100], [100, 100]), ([100, 100], [100, 100])),
                ("oppB", "B", 2, ([130, 100], [100, 110]), ([100, 100], [100, 100])),
            ]:
                self.game(a, "v31", opp, 0, v31[0], family, sub)
                self.game(a, "v31", opp, 1, v31[1], family, sub)
                self.game(b, "v4", opp, 0, v4[0], family, sub)
                self.game(b, "v4", opp, 1, v4[1], family, sub)
            report = rg.reduce_roots([a], [b], expected_cells=4)
            self.assertTrue(report["panel_complete"])
            self.assertEqual(report["summary"]["count"], 4)
            self.assertEqual(report["regression_hotspots"][0]["opponent"], "oppB")
            self.assertEqual(report["regression_hotspots"][0]["margin_delta_v31_minus_v4"], 30)
            self.assertEqual([r["family"] for r in report["by_family"]], ["B", "A"])

    def test_missing_pair_is_non_authorizing_not_silent(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.root(td, "v31"), self.root(td, "v4")
            self.game(a, "v31", "opp", 0, [110, 100])
            report = rg.reduce_roots([a], [b], expected_cells=2)
            self.assertFalse(report["panel_complete"])
            self.assertEqual(report["missing_v4"], [{"opponent": "opp", "seat": 0}])

    def test_candidate_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            a = self.root(td, "v31")
            b = self.root(td, "v4")
            run = json.loads((a / "run.json").read_text())
            run["candidate_sha256"] = "0" * 64
            write_json(a / "run.json", run)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], expected_cells=1)

    def test_cross_version_metadata_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.root(td, "v31"), self.root(td, "v4")
            self.game(a, "v31", "opp", 0, [110, 100], family="A")
            self.game(b, "v4", "opp", 0, [100, 100], family="B")
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], expected_cells=1)

    def test_duplicate_cell_across_roots_fails(self):
        with tempfile.TemporaryDirectory() as td:
            a0 = self.root(td, "v31", 0, 2)
            a1 = self.root(td, "v31", 1, 2)
            b = self.root(td, "v4")
            self.game(a0, "v31", "opp", 0, [110, 100])
            self.game(a1, "v31", "opp", 0, [110, 100])
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a0, a1], [b], expected_cells=1)

    def test_complete_game_wrong_callback_count_fails(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.root(td, "v31"), self.root(td, "v4")
            self.game(a, "v31", "opp", 0, [110, 100], steps=718)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], expected_cells=1)

    def test_cli_partial_writes_report_and_returns_three(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = self.root(td, "v31"), self.root(td, "v4")
            out = Path(td) / "report.json"
            self.game(a, "v31", "opp", 0, [110, 100])
            self.game(b, "v4", "opp", 0, [100, 100])
            code = rg.main([
                "--v31-root", str(a),
                "--v4-root", str(b),
                "--expected-cells", "2",
                "--output", str(out),
            ])
            self.assertEqual(code, 3)
            self.assertTrue(out.exists())
            self.assertFalse(json.loads(out.read_text())["panel_complete"])


if __name__ == "__main__":
    unittest.main()
