#!/usr/bin/env python3
"""Incoming-models map. Screenshot payload only. Not a Commons gate."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import incoming_models as im  # noqa: E402


class IncomingModelsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = im.load_map()
        self.card = (ROOT / "ground" / "INCOMING_MODELS.md").read_text(encoding="utf-8")
        self.html = im.render_html(self.data)
        self.alert = (ROOT / "p" / "cursor-big-things-incoming-alert-20260902-01.md").read_text(
            encoding="utf-8"
        )

    def test_map_is_not_a_commons_gate(self) -> None:
        self.assertEqual(self.data["id"], "incoming-models-hub-payload-20260902-01")
        self.assertIs(self.data["gate"], False)
        self.assertIs(self.data["commons_admission"], False)
        self.assertIs(self.data["invented_access"], False)
        self.assertIs(self.data["invented_payload"], False)
        self.assertIs(self.data["did_not_probe_provider"], True)
        self.assertEqual(self.data["cash_usd"], 0)
        self.assertEqual(self.data["hub"]["ts"], "1788380844.707619")
        self.assertEqual(self.data["hub"]["channel"], "C0BU51F1PL3")

    def test_leftover_alert_not_reminted(self) -> None:
        self.assertIn("id: cursor-big-things-incoming-alert-20260902-01", self.alert)
        self.assertEqual(
            self.data["did_not_remint_alert"],
            "cursor-big-things-incoming-alert-20260902-01",
        )
        self.assertIn("Did not invent what the big things are", self.alert)
        self.assertIn("cursor-big-things-incoming-alert-20260902-01", self.card)

    def test_screenshot_payload_named(self) -> None:
        by_id = {row["id"]: row for row in self.data["models"]}
        self.assertEqual(by_id["muse-spark-1.3"]["evidence"], "SCREENSHOT_CLAIM")
        self.assertFalse(by_id["muse-spark-1.3"]["reachable_here"])
        self.assertEqual(by_id["muse-spark-1.3"]["slack_file"], "F0BVDSJSUU8")
        self.assertEqual(by_id["gpt-6-astra"]["evidence"], "THIRD_PARTY_PROBE")
        self.assertIn("GATED-EXISTS", by_id["gpt-6-astra"]["probe_result"])
        self.assertFalse(by_id["gpt-6-astra"]["reachable_here"])
        self.assertEqual(by_id["gpt-6-astra"]["slack_file"], "F0BU44LE3AT")
        self.assertTrue(by_id["gpt-5.6-sol"]["reachable_here"])
        self.assertTrue(by_id["opus-5"]["reachable_here"])
        self.assertTrue(by_id["fable-5.1"]["reachable_here"])

    def test_check_passes(self) -> None:
        report = im.check(self.data)
        self.assertTrue(report["ok"], report)
        self.assertEqual(
            report["reachable_here"],
            ["gpt-5.6-sol", "opus-5", "fable-5.1"],
        )
        self.assertIn("muse-spark-1.3", report["absent_here"])
        self.assertIn("gpt-6-astra", report["absent_here"])

    def test_reachable_classifier(self) -> None:
        prefixes = self.data["this_seat"]["slug_prefixes"]
        self.assertTrue(
            im.reachable({"slug_prefixes": ["gpt-5.6-sol"]}, prefixes)
        )
        self.assertTrue(
            im.reachable({"slug_prefixes": ["claude-opus-5"]}, prefixes)
        )
        self.assertFalse(im.reachable({"slug_prefixes": []}, prefixes))
        self.assertFalse(
            im.reachable({"slug_prefixes": ["muse-spark-1.3"]}, prefixes)
        )
        self.assertFalse(
            im.reachable({"slug_prefixes": ["gpt-6-astra"]}, prefixes)
        )

    def test_card_and_html_name_files_without_auth(self) -> None:
        for text in (self.card, self.html):
            self.assertIn("1788380844.707619", text)
            self.assertIn("F0BVDSJSUU8", text)
            self.assertIn("F0BU44LE3AT", text)
            self.assertIn("Muse Spark 1.3", text)
            self.assertIn("gpt-6-astra", text)
            self.assertNotIn("required login", text.lower())
            self.assertNotIn("api-key", text.lower())
            self.assertNotIn("password", text.lower())
        self.assertIn('name="robots" content="index,follow"', self.html)
        self.assertIn("No login", self.html)
        self.assertIn("ACTION PAD", self.html)

    def test_cli_check_and_write_html(self) -> None:
        out = subprocess.check_output(
            [sys.executable, str(ROOT / "host" / "incoming_models.py"), "--check"],
            cwd=ROOT,
            text=True,
        )
        report = json.loads(out)
        self.assertTrue(report["ok"])
        written = im.write_html()
        self.assertTrue(written.exists())
        body = written.read_text(encoding="utf-8")
        self.assertIn("muse-spark-1.3", body)
        self.assertIn("gpt-6-astra", body)
        self.assertIn("REACHABLE_HERE", body)
        self.assertIn("ABSENT_HERE", body)

    def test_does_not_steal_autogtm_leftovers(self) -> None:
        keep = " ".join(self.data["keep_unread"])
        self.assertIn("9d8b3e85", keep)
        self.assertIn("14eeedb0", keep)
        self.assertIn("92c4e31f", keep)


if __name__ == "__main__":
    unittest.main()
