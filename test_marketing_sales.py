from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("marketing_sales", ROOT / "host" / "marketing_sales.py")
assert SPEC and SPEC.loader
marketing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(marketing)


def repo(login: str, name: str, owner_type: str = "Organization", stars: int = 20) -> dict:
    return {
        "owner": {"login": login, "type": owner_type},
        "full_name": f"{login}/{name}",
        "html_url": f"https://github.com/{login}/{name}",
        "pushed_at": "2026-08-30T00:00:00Z",
        "stargazers_count": stars,
    }


def config(*queries: dict) -> dict:
    return {
        "schema_version": marketing.DISCOVERY_VERSION,
        "kind": "MARKETING_SALES_DISCOVERY_QUERIES",
        "configured_at": "2026-08-30T00:00:00Z",
        "source": "GitHub public repository search",
        "queries": list(queries),
    }


class MarketingSalesTests(unittest.TestCase):
    def test_discovery_clusters_repositories_by_public_owner_without_qualification(self) -> None:
        payloads = [
            {"items": [repo("AcmeAI", "agent"), repo("Solo", "bot", "User", 2)]},
            {"items": [repo("AcmeAI", "runtime", stars=200), repo("Other", "ops")]},
        ]

        def fetcher(_: str) -> dict:
            return payloads.pop(0)

        result = marketing.discover(
            config(
                {"id": "one", "query": "topic:ai-agent", "pages": 1},
                {"id": "two", "query": "topic:agentic-ai", "pages": 1},
            ),
            per_page=100,
            fetcher=fetcher,
        )
        self.assertEqual(result["truth"]["source_results"], 4)
        self.assertEqual(result["truth"]["research_entities"], 3)
        self.assertEqual(result["truth"]["github_organization_entities"], 2)
        acme = next(item for item in result["entities"] if item["entity_name"] == "AcmeAI")
        self.assertEqual(acme["source_query_ids"], ["one", "two"])
        self.assertEqual(len(acme["repositories"]), 2)
        self.assertEqual(acme["qualification_state"], "RESEARCH_REQUIRED")
        self.assertEqual(result["truth"]["evidence_qualified_accounts"], 0)
        self.assertEqual(result["truth"]["transport_actions"], 0)

    def test_discovery_respects_account_floor_without_counting_results_as_accounts(self) -> None:
        payload = {"items": [repo("One", "a"), repo("One", "b"), repo("Two", "c")]}
        result = marketing.discover(
            config({"id": "one", "query": "topic:ai-agent", "pages": 1}),
            per_page=100,
            max_entities=2,
            fetcher=lambda _: payload,
        )
        self.assertEqual(result["truth"]["source_results"], 3)
        self.assertEqual(result["truth"]["research_entities"], 2)

    def test_every_query_executes_before_deterministic_entity_cap(self) -> None:
        payloads = [
            {"items": [repo("FirstUser", "one", "User", 1), repo("SecondUser", "two", "User", 1)]},
            {"items": [repo("LaterOrganization", "agent", "Organization", 200)]},
        ]
        result = marketing.discover(
            config(
                {"id": "low-intent", "query": "topic:generic", "pages": 1},
                {"id": "high-intent", "query": "agent reliability in:readme", "pages": 1},
            ),
            max_entities=2,
            fetcher=lambda _: payloads.pop(0),
            observed_at=marketing.parse_time("2026-08-30T01:00:00Z"),
        )
        self.assertEqual(result["truth"]["source_queries"], 2)
        self.assertEqual(result["truth"]["source_results"], 3)
        self.assertIn("LaterOrganization", {item["entity_name"] for item in result["entities"]})

    def test_incomplete_search_response_is_rejected(self) -> None:
        with self.assertRaises(marketing.MarketingSalesError):
            marketing.discover(
                config({"id": "one", "query": "topic:ai-agent", "pages": 1}),
                fetcher=lambda _: {"incomplete_results": True, "items": [repo("Acme", "agent")]},
            )

    def test_unknown_fields_duplicate_queries_and_self_qualification_fail(self) -> None:
        duplicate = config(
            {"id": "same", "query": "one", "pages": 1},
            {"id": "same", "query": "two", "pages": 1},
        )
        with self.assertRaises(marketing.MarketingSalesError):
            marketing.validate_queries(duplicate)
        invalid = marketing.discover(
            config({"id": "one", "query": "one", "pages": 1}),
            fetcher=lambda _: {"items": [repo("Acme", "agent")]},
        )
        invalid["entities"][0]["qualification_state"] = "QUALIFIED"
        with self.assertRaises(marketing.MarketingSalesError):
            marketing.validate_universe(invalid)

    def test_public_projection_rejects_email_addresses(self) -> None:
        universe = marketing.discover(
            config({"id": "one", "query": "one", "pages": 1}),
            fetcher=lambda _: {"items": [repo("Acme", "agent")]},
        )
        universe["entities"][0]["entity_name"] = "owner@example.test"
        with self.assertRaises(marketing.MarketingSalesError):
            marketing.validate_universe(universe)

    def test_universe_rejects_tampered_truth_identity_provenance_score_time_and_secret(self) -> None:
        universe = marketing.discover(
            config({"id": "one", "query": "one", "pages": 1}),
            fetcher=lambda _: {"items": [repo("Acme", "agent")]},
            observed_at=marketing.parse_time("2026-08-30T01:00:00Z"),
        )
        variants = []
        negative = copy.deepcopy(universe)
        negative["truth"]["source_results"] = -1
        variants.append(negative)
        identity = copy.deepcopy(universe)
        identity["entities"][0]["entity_id"] = "github:Fabricated"
        variants.append(identity)
        score = copy.deepcopy(universe)
        score["entities"][0]["research_score"] -= 1
        variants.append(score)
        provenance = copy.deepcopy(universe)
        provenance["entities"][0]["repositories"][0]["url"] = "https://github.com/Other/fake"
        variants.append(provenance)
        future = copy.deepcopy(universe)
        future["entities"][0]["repositories"][0]["pushed_at"] = "2026-08-30T01:00:01Z"
        variants.append(future)
        secret = copy.deepcopy(universe)
        secret_name = "sk_live_" + "A" * 24
        secret["entities"][0]["repositories"][0]["full_name"] = f"Acme/{secret_name}"
        secret["entities"][0]["repositories"][0]["url"] = f"https://github.com/Acme/{secret_name}"
        variants.append(secret)
        for variant in variants:
            with self.subTest(variant=variants.index(variant)):
                with self.assertRaises(marketing.MarketingSalesError):
                    marketing.validate_universe(variant)

    def test_compiler_keeps_seed_truth_separate_from_sales_qualification(self) -> None:
        universe = marketing.discover(
            config({"id": "one", "query": "one", "pages": 1}),
            fetcher=lambda _: {"items": [repo(f"Org{index}", "agent") for index in range(60)]},
        )
        pipeline = marketing.compile_pipeline(universe, marketing.read_object(marketing.DEFAULT_CONTRACT))
        self.assertEqual(pipeline["current"]["research_entities"], 60)
        self.assertEqual(pipeline["current"]["evidence_qualified_accounts"], 0)
        self.assertEqual(pipeline["current"]["verified_business_routes"], 0)
        self.assertEqual(len(pipeline["research_queue"]), 50)
        self.assertEqual(pipeline["seed_audit"]["source_rows_labeled_qualified"], 14)
        self.assertEqual(pipeline["seed_audit"]["verified_organizations_in_seed"], 3)
        self.assertEqual(pipeline["seed_audit"]["public_email_routes_in_seed"], 1)
        self.assertEqual(pipeline["seed_audit"]["production_survival_sends"], 1)
        self.assertEqual(pipeline["current"]["cash_usd"], 0)

    def test_pipeline_rejects_false_counts_gaps_queue_and_boundaries(self) -> None:
        universe = marketing.discover(
            config({"id": "one", "query": "one", "pages": 1}),
            fetcher=lambda _: {"items": [repo("Acme", "agent")]},
        )
        contract = marketing.read_object(marketing.DEFAULT_CONTRACT)
        pipeline = marketing.compile_pipeline(universe, contract)
        variants = []
        count = copy.deepcopy(pipeline)
        count["current"]["research_entities"] = 99
        variants.append(count)
        gap = copy.deepcopy(pipeline)
        gap["gap"]["research_entities"] = 0
        variants.append(gap)
        queue = copy.deepcopy(pipeline)
        queue["research_queue"][0]["entity_name"] = "Fabricated"
        variants.append(queue)
        boundary = copy.deepcopy(pipeline)
        boundary["boundaries"]["private_routes_or_provider_ids_published"] = True
        variants.append(boundary)
        for variant in variants:
            with self.subTest(variant=variants.index(variant)):
                with self.assertRaises(marketing.MarketingSalesError):
                    marketing.validate_pipeline(variant, universe=universe, contract=contract)

    def test_contract_rejects_false_funnel_math(self) -> None:
        contract = marketing.read_object(marketing.DEFAULT_CONTRACT)
        contract["goal"]["weekly_gross_captured_usd"] += 1
        with self.assertRaises(marketing.MarketingSalesError):
            marketing.validate_contract(contract)

    def test_checked_in_projection_validates_and_rebuilds_exactly(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "host" / "marketing_sales.py"), "validate"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertRegex(
            result.stdout.strip(),
            r"^VALID \d+ research entities \d+ GitHub organizations 50 queued; 0 qualified 0 routes 0 sends USD 0 cash$",
        )


if __name__ == "__main__":
    unittest.main()
