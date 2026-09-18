#!/usr/bin/env python3
"""Exercise real marketing-sales validation on imported JSON shapes, without I/O providers."""
from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "host" / "marketing_sales.py"
SPEC = importlib.util.spec_from_file_location("marketing_sales_input_shapes", SOURCE)
assert SPEC and SPEC.loader
sales = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sales)


def universe() -> dict:
    """Synthetic, valid source records; these are not a customer or sales claim."""
    return {
        "schema_version": sales.UNIVERSE_VERSION,
        "kind": "MARKETING_SALES_RESEARCH_UNIVERSE",
        "observed_at": "2026-09-08T10:00:00Z",
        "source": "GitHub public repository search",
        "truth": {
            "source_queries": 1, "source_results": 2,
            "research_entities": 1, "github_organization_entities": 1,
            "evidence_qualified_accounts": 0, "verified_business_routes": 0,
            "transport_actions": 0, "cash_usd": 0,
        },
        "entities": [{
            "entity_id": "github:Acme", "entity_name": "Acme",
            "owner_type": "Organization", "qualification_state": "RESEARCH_REQUIRED",
            "research_score": 8, "source_query_ids": ["systems"],
            "repositories": [{
                "full_name": "Acme/alpha", "url": "https://github.com/Acme/alpha",
                "pushed_at": "2026-09-07T10:00:00Z", "stars": 100, "query_id": "systems",
            }, {
                "full_name": "Acme/beta", "url": "https://github.com/Acme/beta",
                "pushed_at": "2026-09-06T10:00:00Z", "stars": 0, "query_id": "systems",
            }],
        }],
    }


def queries() -> dict:
    return {
        "schema_version": sales.DISCOVERY_VERSION,
        "kind": "MARKETING_SALES_DISCOVERY_QUERIES",
        "configured_at": "2026-09-08T10:00:00Z",
        "source": "GitHub public repository search",
        "queries": [{"id": "systems", "query": "synthetic fixture", "pages": 1}],
    }


class MarketingSalesInputShapes(unittest.TestCase):
    def test_valid_json_roundtrip_is_unchanged(self):
        value = json.loads(json.dumps(universe()))
        before = sales.canonical_text(value)
        self.assertIs(sales.validate_universe(value), value)
        self.assertEqual(sales.canonical_text(value), before)
        self.assertEqual(value["entities"][0]["research_score"], 8)

    def test_top_level_validators_reject_nonobjects(self):
        for validator in (sales.validate_queries, sales.validate_contract, sales.validate_universe):
            for value in (None, True, 7, 1.5, [], [{}]):
                with self.subTest(validator=validator.__name__, value=value):
                    with self.assertRaises(sales.MarketingSalesError):
                        validator(value)

    def test_list_of_expected_keys_is_not_an_object(self):
        with self.assertRaises(sales.MarketingSalesError):
            sales.validate_universe(list(universe()))

    def test_missing_and_extra_fields_still_report_differences(self):
        with self.assertRaisesRegex(sales.MarketingSalesError, "fields differ"):
            sales.exact_keys({"extra": 1}, {"expected"}, "fixture")

    def test_entity_names_are_validated_before_sorting(self):
        for invalid in (None, True, 7, 1.5, [], {}):
            with self.subTest(name=invalid):
                value = universe()
                value["entities"][0]["entity_name"] = invalid
                with self.assertRaisesRegex(sales.MarketingSalesError, "entity_name"):
                    sales.validate_universe(value)

    def test_nonobject_entities_use_domain_error(self):
        for invalid in (None, False, 7, "Acme", [], ["Acme"]):
            with self.subTest(entity=invalid):
                value = universe()
                value["entities"] = [invalid]
                with self.assertRaisesRegex(sales.MarketingSalesError, "must be an object"):
                    sales.validate_universe(value)

    def test_unhashable_owner_types_use_domain_error(self):
        for invalid in ([], {}, ["Organization"]):
            with self.subTest(owner_type=invalid):
                value = universe()
                value["entities"][0]["owner_type"] = invalid
                with self.assertRaisesRegex(sales.MarketingSalesError, "owner_type"):
                    sales.validate_universe(value)

    def test_repository_rows_are_validated_before_sorting(self):
        for invalid in (None, False, 7, "Acme/alpha", [], ["Acme/alpha"]):
            with self.subTest(repository=invalid):
                value = universe()
                value["entities"][0]["repositories"][0] = invalid
                with self.assertRaisesRegex(sales.MarketingSalesError, "entries must be objects"):
                    sales.validate_universe(value)

    def test_nested_repository_fields_keep_domain_diagnostics(self):
        for field, invalid in (("full_name", []), ("query_id", {}), ("pushed_at", None), ("stars", True)):
            with self.subTest(field=field):
                value = universe()
                value["entities"][0]["repositories"][0][field] = invalid
                with self.assertRaises(sales.MarketingSalesError):
                    sales.validate_universe(value)

    def test_unsorted_valid_repositories_are_not_silently_reordered(self):
        value = universe()
        value["entities"][0]["repositories"].reverse()
        before = copy.deepcopy(value)
        with self.assertRaisesRegex(sales.MarketingSalesError, "repositories must be canonically sorted"):
            sales.validate_universe(value)
        self.assertEqual(value, before)

    def test_unsorted_valid_entities_are_rejected(self):
        value = universe()
        second = copy.deepcopy(value["entities"][0])
        second["entity_name"] = "Beta"
        second["entity_id"] = "github:Beta"
        for repo in second["repositories"]:
            repo["full_name"] = repo["full_name"].replace("Acme/", "Beta/")
            repo["url"] = "https://github.com/" + repo["full_name"]
        value["entities"].insert(0, second)
        value["truth"].update(source_results=4, research_entities=2, github_organization_entities=2)
        with self.assertRaisesRegex(sales.MarketingSalesError, "entities must be canonically sorted"):
            sales.validate_universe(value)
        value["entities"].reverse()
        self.assertIs(sales.validate_universe(value), value)

    def test_duplicate_provenance_is_still_rejected(self):
        value = universe()
        rows = value["entities"][0]["repositories"]
        rows.insert(0, copy.deepcopy(rows[0]))
        with self.assertRaisesRegex(sales.MarketingSalesError, "duplicate provenance"):
            sales.validate_universe(value)

    def test_research_score_is_still_evidence_derived(self):
        value = universe()
        value["entities"][0]["research_score"] = 10
        with self.assertRaisesRegex(sales.MarketingSalesError, "research_score does not match evidence"):
            sales.validate_universe(value)

    def test_query_provenance_must_still_match(self):
        value = universe()
        value["entities"][0]["source_query_ids"] = ["other-query", "systems"]
        with self.assertRaisesRegex(sales.MarketingSalesError, "do not match repository provenance"):
            sales.validate_universe(value)

    def test_future_repository_time_is_still_rejected(self):
        value = universe()
        value["entities"][0]["repositories"][0]["pushed_at"] = "2026-09-09T10:00:00Z"
        with self.assertRaisesRegex(sales.MarketingSalesError, "exceeds observed_at"):
            sales.validate_universe(value)

    def test_qualification_and_truth_counts_do_not_expand(self):
        for field, invalid in (("qualification_state", "QUALIFIED"), ("research_score", True)):
            with self.subTest(field=field):
                value = universe()
                value["entities"][0][field] = invalid
                with self.assertRaises(sales.MarketingSalesError):
                    sales.validate_universe(value)
        for key in ("cash_usd", "transport_actions", "evidence_qualified_accounts", "verified_business_routes"):
            with self.subTest(truth=key):
                value = universe()
                value["truth"][key] = 1
                with self.assertRaisesRegex(sales.MarketingSalesError, "must remain zero"):
                    sales.validate_universe(value)

    def test_discovery_skips_malformed_owner_type_without_losing_valid_rows(self):
        valid = {
            "owner": {"login": "Acme", "type": "Organization"},
            "full_name": "Acme/alpha", "html_url": "https://github.com/Acme/alpha",
            "pushed_at": "2026-09-07T10:00:00Z", "stargazers_count": 100,
        }
        for invalid in ([], {}, ["Organization"]):
            with self.subTest(owner_type=invalid):
                bad = copy.deepcopy(valid)
                bad["owner"]["type"] = invalid
                result = sales.discover(
                    queries(), fetcher=lambda _: {"items": [bad, valid]},
                    observed_at=dt.datetime(2026, 9, 8, 10, tzinfo=dt.timezone.utc),
                )
                self.assertEqual(result["truth"]["source_results"], 2)
                self.assertEqual(result["truth"]["research_entities"], 1)
                self.assertEqual(result["entities"][0]["research_score"], 8)
                self.assertEqual(result["truth"]["transport_actions"], 0)

    def test_cli_bad_import_keeps_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            imported, contract, output = (root / name for name in ("universe.json", "contract.json", "pipeline.json"))
            value = universe()
            value["entities"][0]["repositories"][0] = None
            imported.write_text(json.dumps(value), encoding="utf-8")
            contract.write_text("{}", encoding="utf-8")
            output.write_bytes(b"preserved output\n")
            result = subprocess.run(
                [sys.executable, str(SOURCE), "compile", "--universe", str(imported),
                 "--contract", str(contract), "--output", str(output)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("MarketingSalesError:", result.stderr)
            self.assertNotIn("AttributeError:", result.stderr)
            self.assertEqual(output.read_bytes(), b"preserved output\n")


if __name__ == "__main__":
    unittest.main()
