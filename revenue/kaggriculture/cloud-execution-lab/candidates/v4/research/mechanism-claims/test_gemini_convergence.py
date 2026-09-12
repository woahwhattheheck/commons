import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ATLAS = HERE / "GEMINI-CONVERGENCE.json"

REQUIRED_SEAMS = {
    "melon_cap", "fert_warehouse", "goose_printer", "hoist",
    "structure_carpet", "weedbank", "altwater", "plantguard", "demandvel",
    "expandtax", "dynfloor", "ambush", "starve_skip", "decay_trap",
    "npc_market_baseline", "legacy_g01_e11", "legacy_g01_o01",
    "legacy_g01_e20", "legacy_g01_shop", "legacy_s33_stratum",
    "gemini_pro_capital", "gemini_flash_market", "gemini_idle_service",
}
REQUIRED_APEX = {
    "weed_auto_dig_shield", "clone_radar_front_run",
    "protected_fert_monetization", "early_cash_emergency", "shed_guard",
    "town_shop_microbatch", "predator_market_ambush",
    "late_carrot_seed_guarantee", "endgame_liquidation",
}
REQUIRED_METAGAME = {
    "direct_crop_short_squeeze", "seed_crack_frame_advance",
    "egg_singularity", "goose_radar_invisibility",
}


class GeminiConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(ATLAS.read_text(encoding="utf-8"))

    def test_one_v4_no_runtime_promotion(self):
        self.assertEqual(self.doc["schema"], "titan-v4-gemini-convergence/v1")
        self.assertTrue(self.doc["policy"]["one_v4"])
        self.assertFalse(self.doc["policy"]["new_controller"])
        self.assertFalse(self.doc["policy"]["runtime_activation_implied"])

    def test_every_named_gemini_seam_has_exactly_one_disposition(self):
        items = self.doc["gemini_seams"]
        ids = [item["id"] for item in items]
        self.assertEqual(set(ids), REQUIRED_SEAMS)
        self.assertEqual(len(ids), len(set(ids)))
        for item in items:
            self.assertTrue(item["status"])
            self.assertTrue(item["canonical_surface"])
            self.assertTrue(item["best_form"])
            self.assertTrue(item["promotion_gate"])
            self.assertTrue(item["evidence_prs"])
            self.assertEqual(item["evidence_prs"], sorted(set(item["evidence_prs"])))
            self.assertTrue(item["do_not_resurrect"])

    def test_all_apex_handoff_motifs_are_routed(self):
        motifs = self.doc["apex_handoff_motifs"]
        ids = [item["id"] for item in motifs]
        self.assertEqual(set(ids), REQUIRED_APEX)
        self.assertEqual(len(ids), len(set(ids)))
        for item in motifs:
            self.assertTrue(item["v4_sink"])
            self.assertTrue(item["disposition"])

    def test_all_later_metagame_posts_have_exact_dispositions(self):
        posts = self.doc["metagame_posts"]
        ids = [item["id"] for item in posts]
        self.assertEqual(set(ids), REQUIRED_METAGAME)
        self.assertEqual(len(ids), len(set(ids)))
        for item in posts:
            self.assertTrue(item["status"])
            self.assertTrue(item["canonical_surface"])
            self.assertTrue(item["best_form"])
            self.assertTrue(item["promotion_gate"])
            self.assertTrue(item["evidence_prs"])
            self.assertEqual(item["evidence_prs"], sorted(set(item["evidence_prs"])))
            self.assertTrue(item["do_not_resurrect"])

    def test_known_false_forms_cannot_be_silent(self):
        by_id = {item["id"]: item for item in self.doc["gemini_seams"]}
        meta = {item["id"]: item for item in self.doc["metagame_posts"]}
        self.assertIn("$1 market warehouse", by_id["fert_warehouse"]["do_not_resurrect"])
        self.assertEqual(by_id["altwater"]["status"], "SAFETY_BLOCKED")
        self.assertIn("blind fixed-28 runtime gate", by_id["melon_cap"]["do_not_resurrect"])
        self.assertIn("fractional transition math", by_id["legacy_g01_shop"]["do_not_resurrect"])
        self.assertIn("per-unit graceful seed depletion", by_id["plantguard"]["do_not_resurrect"])
        self.assertIn("BUY_PRODUCT EGG squeeze", meta["direct_crop_short_squeeze"]["do_not_resurrect"])
        self.assertIn("weed pattern implies globally unique seed", meta["seed_crack_frame_advance"]["do_not_resurrect"])
        self.assertIn("infinite EGG floor", meta["egg_singularity"]["do_not_resurrect"])

    def test_melon_successor_is_explicit(self):
        melon = next(x for x in self.doc["gemini_seams"] if x["id"] == "melon_cap")
        self.assertEqual(
            melon["this_change"],
            "repairs/gameplay/antigravity-melon-cap/liquidation_bound.py",
        )
        self.assertIn("realization certificate", melon["promotion_gate"].lower())

    def test_e11_o01_share_policy_inert_public_certificate(self):
        by_id = {item["id"]: item for item in self.doc["gemini_seams"]}
        expected = "research/market-baseline/gemini_market_certificate.py"
        self.assertEqual(by_id["legacy_g01_e11"]["this_change"], expected)
        self.assertEqual(by_id["legacy_g01_o01"]["this_change"], expected)
        self.assertIn("never mutates", by_id["legacy_g01_e11"]["best_form"])
        self.assertIn("one-way public evidence", by_id["legacy_g01_o01"]["best_form"])

    def test_s33_requires_final_downstream_and_returned_action_evidence(self):
        s33 = next(x for x in self.doc["gemini_seams"] if x["id"] == "legacy_s33_stratum")
        self.assertIn("downstream canonical market-pressure", s33["best_form"])
        self.assertIn("returned to the engine", s33["promotion_gate"])
        self.assertIn("pre-pressure rank-difference-only novelty", s33["do_not_resurrect"])

    def test_demandvel_consumes_latest_absorption_headroom(self):
        demand = next(x for x in self.doc["gemini_seams"] if x["id"] == "demandvel")
        self.assertIn(13018, demand["evidence_prs"])
        self.assertIn("absorption headroom", demand["best_form"])
        self.assertIn("no decision or timing authority", demand["best_form"])


if __name__ == "__main__":
    unittest.main()
