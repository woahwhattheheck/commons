#!/usr/bin/env python3
"""Strict JSON input semantics without changing valid rating classifications.

All input files are synthetic. Real subprocesses use isolated complete source
copies; tests do not depend on any live catalog, advertising file, or receipt.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent / "host" / "business_pack_rating.py"
spec = importlib.util.spec_from_file_location("rating_input_contract", SOURCE)
assert spec is not None and spec.loader is not None
rating = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rating)

LAW = {
    "id": "synthetic-rating-law",
    "unique_pack_id": "synthetic-pack",
    "badge_url": "",
    "report_url": "",
    "partner_name": "OWNER_UNSET",
    "bulk_price": "OWNER_UNSET",
}
LINKS = {
    "badge_url": "https://example.invalid/badge.png",
    "report_url": "https://example.invalid/report.pdf",
}


class InputContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.law_path = self.root / "law.json"
        self.law_path.write_text(json.dumps(LAW), encoding="utf-8")

    def classify(self, pack=None):
        return rating.classify_rating(pack, law_path=self.law_path)

    def test_api_none_remains_default_sentinel(self):
        self.assertEqual(self.classify(None), self.classify({}))

    def test_omitted_flag_defaults_to_false(self):
        result = self.classify(LINKS)
        self.assertIs(result["owner_pasted_rating"], False)
        self.assertFalse(result["filled"])
        self.assertEqual(result["verdict"], "RATING_LINK_INVENTED")

    def test_literal_false_is_not_owner_filled(self):
        result = self.classify({**LINKS, "owner_pasted_rating": False})
        self.assertIs(result["owner_pasted_rating"], False)
        self.assertFalse(result["filled"])
        self.assertEqual(result["verdict"], "RATING_LINK_INVENTED")

    def test_literal_true_keeps_existing_result(self):
        result = self.classify({**LINKS, "owner_pasted_rating": True})
        self.assertIs(result["owner_pasted_rating"], True)
        self.assertTrue(result["filled"])
        self.assertEqual(result["verdict"], "RATING_SLOT_OWNER_FILLED")

    def test_falsey_nonobject_packs_raise_value_error(self):
        for value in (False, 0, 0.0, "", [], ()):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "pack must be a JSON object"):
                    self.classify(value)

    def test_truthy_nonobject_packs_raise_value_error(self):
        for value in (True, 1, 1.5, "text", [1], [["owner_pasted_rating", True]]):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "pack must be a JSON object"):
                    self.classify(value)

    def test_string_flags_are_not_booleans(self):
        for value in ("false", "true", "False", "True", "0", "1", "", " "):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "owner_pasted_rating must be a boolean"):
                    self.classify({**LINKS, "owner_pasted_rating": value})

    def test_numeric_flags_are_not_booleans(self):
        for value in (0, 1, -1, 0.0, 1.0, 0.5):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "owner_pasted_rating must be a boolean"):
                    self.classify({**LINKS, "owner_pasted_rating": value})

    def test_container_and_null_flags_are_not_booleans(self):
        for value in (None, [], [False], {}, {"value": False}):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "owner_pasted_rating must be a boolean"):
                    self.classify({**LINKS, "owner_pasted_rating": value})

    def test_rejected_pack_needs_no_law_read(self):
        missing = self.root / "does-not-exist.json"
        with self.assertRaisesRegex(ValueError, "pack must be a JSON object"):
            rating.classify_rating([], law_path=missing)

    def test_rejected_flag_needs_no_law_read(self):
        missing = self.root / "does-not-exist.json"
        with self.assertRaisesRegex(ValueError, "owner_pasted_rating must be a boolean"):
            rating.classify_rating({"owner_pasted_rating": "false"}, law_path=missing)

    def test_dictionary_subclasses_are_accepted(self):
        class Pack(dict):
            pass
        self.assertEqual(self.classify(Pack(LINKS)), self.classify(LINKS))

    def test_inputs_and_law_are_not_modified(self):
        pack = {**LINKS, "owner_pasted_rating": True, "extra": {"items": [1, 2]}}
        original = copy.deepcopy(pack)
        before = self.law_path.read_bytes()
        self.classify(pack)
        self.assertEqual(pack, original)
        self.assertEqual(self.law_path.read_bytes(), before)

    def test_selected_law_is_still_selected(self):
        other = self.root / "other-law.json"
        other.write_text(json.dumps({**LAW, "id": "different-law"}), encoding="utf-8")
        result = rating.classify_rating({}, law_path=other)
        self.assertEqual(result["id"], "different-law")
        self.assertEqual(self.classify({})["id"], LAW["id"])

    def test_valid_verdict_precedence_is_unchanged(self):
        cases = [
            ({}, "RATING_SLOT_EMPTY"),
            ({"copy": "Independently audited"}, "RATING_CLAIM_UNSUBSTANTIATED"),
            ({"copy": "make $4"}, "EARNINGS_IN_ADS"),
            ({"copy": "valued at $40"}, "RATING_EARNINGS_CLAIM"),
            ({**LINKS, "owner_pasted_rating": True, "copy": "valued at $40"}, "RATING_EARNINGS_CLAIM"),
            ({**LINKS, "owner_pasted_rating": False, "copy": "valued at $40"}, "RATING_LINK_INVENTED"),
            ({"badge_url": "https://buy.stripe.com/synthetic", "owner_pasted_rating": True}, "RATING_LINK_INVENTED"),
        ]
        for pack, verdict in cases:
            with self.subTest(pack=pack):
                result = self.classify(pack)
                self.assertEqual(result["verdict"], verdict)
                for field in ("gate", "commons_admission", "agents_pick_partner", "agents_invent_bulk_price", "agents_spend_ads"):
                    self.assertIs(result[field], False)
                self.assertEqual(result["checkout"], "NOT_MINTED")


class CLIContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "host").mkdir()
        (self.root / "ground").mkdir()
        self.script = self.root / "host" / "business_pack_rating.py"
        shutil.copyfile(SOURCE, self.script)
        (self.root / "ground" / "BUSINESS_PACK_RATING.json").write_text(json.dumps(LAW), encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(self.script), *args], text=True,
                              capture_output=True, check=False, timeout=10, cwd=self.root)

    def assert_input_error(self, text, expected):
        result = self.run_cli("--pack", text)
        self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
        self.assertEqual(result.stdout, "")
        self.assertIn(expected, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_default_cli_unchanged(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["verdict"], "RATING_SLOT_EMPTY")

    def test_valid_owner_filled_cli(self):
        result = self.run_cli("--pack", json.dumps({**LINKS, "owner_pasted_rating": True}))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["filled"])

    def test_nonobject_json_cli_errors(self):
        for value in (None, False, True, 0, 1, "", "text", [], [["owner_pasted_rating", True]]):
            with self.subTest(value=repr(value)):
                self.assert_input_error(json.dumps(value), "--pack must be a JSON object")

    def test_malformed_flag_cli_errors(self):
        for value in ("false", "true", 0, 1, [], {}, None):
            with self.subTest(value=repr(value)):
                self.assert_input_error(json.dumps({**LINKS, "owner_pasted_rating": value}),
                                        "owner_pasted_rating must be a boolean")

    def test_malformed_json_is_concise_cli_error(self):
        self.assert_input_error('{"unfinished":', "error:")


if __name__ == "__main__":
    unittest.main()
