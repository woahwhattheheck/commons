from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import gauntlet_panel_identity as g

H = lambda c: c * 64


def panel() -> dict:
    return {
        "schema": g.SCHEMA,
        "panel_id": "synthetic-panel",
        "opponents": [
            {"id": "sheep-a", "kind": "archetype", "family_id": "sheep-shift", "variant_id": "a", "source_sha256": H("a"), "wins": 0, "losses": 2, "draws": 0, "total_margin": -200},
            {"id": "sheep-a-alias", "kind": "archetype", "family_id": "sheep-shift", "variant_id": "alias", "source_sha256": H("a"), "wins": 0, "losses": 2, "draws": 0, "total_margin": -200},
            {"id": "sheep-b", "kind": "archetype", "family_id": "sheep-shift", "variant_id": "b", "source_sha256": H("b"), "wins": 1, "losses": 1, "draws": 0, "total_margin": 0},
            {"id": "wheat-a", "kind": "archetype", "family_id": "wheat-pump", "variant_id": "a", "source_sha256": H("c"), "wins": 2, "losses": 0, "draws": 0, "total_margin": 400},
        ],
    }


class PanelIdentityTests(unittest.TestCase):
    def test_counts_families_sources_and_aliases(self):
        r = g.audit(panel())
        self.assertEqual(r["raw_label_count"], 4)
        self.assertEqual(r["family_count"], 2)
        self.assertEqual(r["unique_source_count"], 3)
        self.assertEqual(r["alias_excess"], 1)
        self.assertEqual(r["multiplicity"], {"sheep-shift": 3})
        self.assertEqual(r["alias_groups"][0]["labels"], ["sheep-a", "sheep-a-alias"])

    def test_family_balance_removes_label_multiplicity(self):
        r = g.audit(panel())
        self.assertEqual(r["views"]["raw_label_mean"]["mean_margin"], "0")
        self.assertEqual(r["views"]["family_balanced_mean"]["mean_margin"], "75")

    def test_source_balance_collapses_exact_aliases(self):
        r = g.audit(panel())
        self.assertEqual(r["views"]["source_balanced_mean"]["mean_margin"], "33.333333333333333333333333333333333333333333333333")

    def test_raw_counts_remain_visible(self):
        r = g.audit(panel())
        self.assertEqual(r["views"]["raw_game_weighted_counts"], {
            "games": 8, "wins": 3, "losses": 5, "draws": 0, "total_margin": 0,
        })

    def test_identity_only_panel_supported(self):
        p = panel()
        for row in p["opponents"]:
            for key in ("wins", "losses", "draws", "total_margin"):
                row.pop(key)
        r = g.audit(p)
        self.assertFalse(r["outcomes_present"])
        self.assertNotIn("views", r)

    def test_mixed_outcome_presence_fails(self):
        p = panel()
        for key in ("wins", "losses", "draws", "total_margin"):
            p["opponents"][0].pop(key)
        with self.assertRaisesRegex(g.IdentityError, "mixes identity-only"):
            g.audit(p)

    def test_partial_outcome_fails(self):
        p = panel()
        p["opponents"][0].pop("draws")
        with self.assertRaisesRegex(g.IdentityError, "outcomes must provide"):
            g.audit(p)

    def test_duplicate_id_fails(self):
        p = panel()
        p["opponents"][1]["id"] = p["opponents"][0]["id"]
        with self.assertRaisesRegex(g.IdentityError, "duplicate opponent id"):
            g.audit(p)

    def test_duplicate_variant_within_family_fails(self):
        p = panel()
        p["opponents"][1]["variant_id"] = "a"
        with self.assertRaisesRegex(g.IdentityError, "duplicate variant_id"):
            g.audit(p)

    def test_same_source_cannot_be_laundered_across_families(self):
        p = panel()
        p["opponents"][-1]["source_sha256"] = H("a")
        with self.assertRaisesRegex(g.IdentityError, "conflicting family/kind"):
            g.audit(p)

    def test_same_source_cannot_change_kind(self):
        p = panel()
        p["opponents"][1]["kind"] = "recorded_trace"
        with self.assertRaisesRegex(g.IdentityError, "conflicting family/kind"):
            g.audit(p)

    def test_mirror_cannot_share_nonmirror_family(self):
        p = panel()
        p["opponents"][0]["kind"] = "mirror"
        p["opponents"][0]["source_sha256"] = H("d")
        with self.assertRaisesRegex(g.IdentityError, "mixes mirror"):
            g.audit(p)

    def test_bool_count_fails(self):
        p = panel()
        p["opponents"][0]["wins"] = True
        with self.assertRaisesRegex(g.IdentityError, "not bool"):
            g.audit(p)

    def test_hash_must_be_lower_hex(self):
        p = panel()
        p["opponents"][0]["source_sha256"] = "A" * 64
        with self.assertRaisesRegex(g.IdentityError, "lowercase SHA-256"):
            g.audit(p)

    def test_zero_game_row_fails(self):
        p = panel()
        row = p["opponents"][0]
        row.update(wins=0, losses=0, draws=0)
        with self.assertRaisesRegex(g.IdentityError, "zero games"):
            g.audit(p)

    def test_duplicate_json_key_fails_before_audit(self):
        with self.assertRaisesRegex(g.IdentityError, "duplicate JSON key"):
            g.loads_strict('{"schema":"x","schema":"y"}')

    def test_large_integer_margin_is_exact(self):
        p = panel()
        huge = 10 ** 300
        p["opponents"][0]["total_margin"] = huge
        r = g.audit(p)
        self.assertEqual(r["views"]["raw_game_weighted_counts"]["total_margin"], huge + 200)
        self.assertNotIn("E+", r["views"]["family_balanced_mean"]["mean_margin"])

    def test_deterministic_order_independent_of_input_order(self):
        a = g.audit(panel())
        p = panel()
        p["opponents"].reverse()
        b = g.audit(p)
        self.assertEqual(a["families"], b["families"])
        self.assertEqual(a["alias_groups"], b["alias_groups"])
        self.assertEqual(a["views"], b["views"])

    def test_promotion_is_never_assessed(self):
        self.assertEqual(g.audit(panel())["promotion_decision"], "NOT_ASSESSED")

    def test_cli_and_optimized_cli_match(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "panel.json"
            src.write_text(json.dumps(panel()), encoding="utf-8")
            cmd = [sys.executable, str(Path(g.__file__)), str(src)]
            normal = subprocess.run(cmd, check=False, capture_output=True, text=True)
            optimized = subprocess.run([sys.executable, "-O", str(Path(g.__file__)), str(src)], check=False, capture_output=True, text=True)
            self.assertEqual(normal.returncode, 0)
            self.assertEqual(optimized.returncode, 0)
            self.assertEqual(normal.stdout, optimized.stdout)

    def test_cli_duplicate_key_returns_two(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "panel.json"
            src.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            run = subprocess.run([sys.executable, str(Path(g.__file__)), str(src)], check=False, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("duplicate JSON key", run.stderr)


if __name__ == "__main__":
    unittest.main()
