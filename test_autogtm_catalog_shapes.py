#!/usr/bin/env python3
"""Regression coverage for AutoGTM prospect-catalog container boundaries."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get("AUTOGTM_SOURCE", ROOT / "host" / "autogtm_same_loop.py"))
SPEC = importlib.util.spec_from_file_location("autogtm_catalog_shapes", SOURCE)
assert SPEC and SPEC.loader
loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loop)

CONTEXT = {
    "source": "fixture",
    "offer": "Agent crash-resume proof",
    "icp": "production agent owner",
    "book_url": None,
    "composed_from": "test",
    "state": "INTEGRATED",
}
VALID_ROWS = [
    {
        "prospect_id": "first",
        "organization": "First Org",
        "recipient_email": "first@example.test",
        "evidence": {"source_url": "https://example.test/first"},
    },
    {
        "prospect_id": "second",
        "organization": "Second Org",
        "recipient_email": None,
        "evidence": None,
    },
]


class CatalogShapeTests(unittest.TestCase):
    def test_nonobject_catalog_roots_are_rejected_explicitly(self) -> None:
        for value in ([], "prospects", 7, True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "catalog must be an object"):
                    loop.search_extract(value)

    def test_prospects_container_must_be_a_list(self) -> None:
        for value in ({}, "row", 7, True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "prospects must be a list"):
                    loop.search_extract({"prospects": value})

    def test_missing_or_null_prospects_preserves_empty_catalog_behavior(self) -> None:
        self.assertEqual(loop.search_extract({}), [])
        self.assertEqual(loop.search_extract({"prospects": None}), [])
        self.assertEqual(loop.search_extract({"prospects": []}), [])

    def test_each_prospect_row_must_be_an_object(self) -> None:
        for value in (None, "row", 7, [], True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "row 1 must be an object"):
                    loop.search_extract({"prospects": [VALID_ROWS[0], value]})

    def test_evidence_is_object_or_null_before_enrichment(self) -> None:
        for value in ("url", [], 7, True):
            row = {**VALID_ROWS[0], "evidence": value}
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "row 0 evidence must be an object or null"):
                    loop.search_extract({"prospects": [row]})

    def test_valid_rows_keep_order_values_and_caller_inputs(self) -> None:
        rows = [dict(row) for row in VALID_ROWS]
        catalog = {"prospects": rows, "other": {"retained": True}}
        before = repr(catalog)
        result = loop.search_extract(catalog)
        self.assertEqual(result, rows)
        self.assertIsNot(result, rows)
        self.assertIs(result[0], rows[0])
        self.assertEqual(repr(catalog), before)

    def test_invalid_catalog_stops_before_provider_probe(self) -> None:
        calls: list[str] = []

        def opener(url: str):
            calls.append(url)
            raise AssertionError("provider probe must not run")

        with mock.patch.object(loop, "set_context", return_value=dict(CONTEXT)):
            with self.assertRaises(ValueError):
                loop.measure(html="<html></html>", source="fixture", catalog=[], opener=opener)
        self.assertEqual(calls, [])

    def test_valid_catalog_retains_scoring_drafts_and_no_send_contract(self) -> None:
        calls: list[str] = []

        def opener(url: str):
            calls.append(url)
            return 401, '{"detail":"Missing API key"}'

        catalog = {"prospects": [dict(row) for row in VALID_ROWS]}
        before = repr(catalog)
        with mock.patch.object(loop, "set_context", return_value=dict(CONTEXT)):
            result = loop.measure(
                html="<html></html>", source="fixture", catalog=catalog,
                asked_autopilot=True, opener=opener,
            )
        self.assertEqual([row["prospect_id"] for row in result["scored"]], ["first", "second"])
        self.assertEqual([row["prospect_id"] for row in result["drafts"]], ["first"])
        self.assertEqual(result["search"]["found"], 2)
        self.assertEqual(result["autopilot"]["state"], "REFUSED")
        self.assertEqual(result["explee_api"]["state"], "FINDER-FAILED")
        self.assertFalse(result["sent"])
        self.assertEqual(result["booked"], 0)
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(calls, [loop.EXPLEE_PROJECTS])
        self.assertEqual(repr(catalog), before)


if __name__ == "__main__":
    unittest.main()
