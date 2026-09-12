#!/usr/bin/env python3
"""Resource ledger leftover measures; it does not count cache as capacity."""

from __future__ import annotations

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from resource_ledger import (
    REQUIRED_FIELDS,
    RESOURCE_CONDITIONS,
    RESOURCE_FRESHNESS_STATES,
    RESOURCE_STAGES,
    V2_REQUIRED_FIELDS,
    catalog_from_row,
    classify,
    classify_surface,
    evidence_freshness,
    load_catalog,
    local_probes,
    measure_from_rows,
    measure_root,
)


LIVE_FIELDS = {
    "evidence_ts": "2026-08-25T06:10:00Z",
    "auth_surface": "GitHub MCP",
    "exact_safe_probe": "get_me",
    "rate_plan_boundary": "one app",
    "assigned_backlog": "current-main writes",
    "last_receipt": "rivet-ship-resource-ledger-20260825-01",
}


class TestResourceLedger(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_secrets_are_not_landed(self):
        row = classify({"measured": True, "secrets": True, "live": ["github"]})
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("secrets", row["note"])

    def test_cache_as_capacity_is_not_landed(self):
        row = classify({"measured": True, "cache_as_capacity": True, "live": ["github"]})
        self.assertEqual(row["state"], "NOT_LANDED")
        self.assertIn("cache was counted as capacity", row["note"])

    def test_huggingface_cache_is_not_live(self):
        row = classify_surface(
            {"name": "huggingface", "capacity": "LIVE", "cache_counted": True},
            {},
        )
        self.assertEqual(row["capacity"], "NOT_VERIFIED")
        self.assertIn("NOT verified", row["note"])

    def test_claude_tester_authority_is_not_landed(self):
        row = classify_surface(
            {
                "name": "claude",
                "capacity": "UNMEASURED",
                "assigned_backlog": "Claude is the review authority and tester",
            },
            {},
        )
        self.assertTrue(row["tester_authority"])
        measured = measure_from_rows(
            {
                "surfaces": [
                    dict(LIVE_FIELDS, name="github", capacity="LIVE"),
                    {
                        "name": "claude",
                        "capacity": "UNMEASURED",
                        "assigned_backlog": "Claude is the review authority and tester",
                    },
                ]
            }
        )
        self.assertTrue(measured["claude_tester_authority"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("tester", classify(measured)["note"])

    def test_claude_informational_row_is_not_authority(self):
        row = classify_surface(
            {
                "name": "claude",
                "capacity": "UNMEASURED",
                "assigned_backlog": "informational evidence only; not tester",
            },
            {},
        )
        self.assertFalse(row["tester_authority"])

    def test_vercel_production_write_is_forbidden(self):
        row = classify_surface(
            {"name": "vercel", "capacity": "LIVE", "production_write": True},
            {},
        )
        self.assertEqual(row["capacity"], "FORBIDDEN")
        self.assertIn("production write", row["note"])

    def test_census_separates_live_from_cache(self):
        github = dict(LIVE_FIELDS)
        github["name"] = "github"
        github["capacity"] = "LIVE"
        measured = measure_from_rows(
            {
                "surfaces": [
                    github,
                    {"name": "huggingface", "capacity": "LIVE", "cache_counted": True},
                    {"name": "zapier", "capacity": "CACHE", "cache_counted": True},
                ],
                "probes": {"hf_token_files": [], "hf_cli": False},
            }
        )
        self.assertIn("github", measured["live"])
        self.assertIn("huggingface", measured["not_verified"])
        self.assertIn("zapier", measured["cache"])
        self.assertFalse(measured["cache_as_capacity"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertFalse(measured["secrets"])
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("Cache is not capacity", verdict["note"])

    def test_live_rows_need_ledger_fields(self):
        measured = measure_from_rows(
            {"surfaces": [{"name": "github", "capacity": "LIVE"}]}
        )
        self.assertTrue(measured["missing_fields"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_catalog_has_required_fields_and_no_secrets(self):
        catalog_path = os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            text = handle.read()
        catalog = load_catalog(text)
        raw = json.loads(text)
        self.assertEqual(catalog["slack_ts"], "1789229283.919009")
        self.assertEqual(
            catalog["source_id"],
            "codex-titan-v5-day-close-animal-feed-certificate-resource-activation-20260912-01",
        )
        self.assertIn(
            "codex-titan-v5-day-close-animal-feed-certificate-resource-activation-20260912-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-v5-cross-evidence-promotion-gate-resource-activation-20260912-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-v5-worker-job-payback-resource-activation-20260912-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-v25-joint-sell-resource-activation-20260909-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-v25-cloud-simulation-order-queue-activation-20260909-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-official-engine-benchmark-evidence-activation-20260909-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-human-outcomes-input-validator-activation-20260909-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-hive-intake-crm-workflow-activation-20260909-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-hive-trade-quote-schedule-activation-20260908-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-gpt-6-astra-carrier-activation-20260908-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-runtime-profiler-activation-20260908-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-cloud-model-lab-activation-20260908-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-commons-operation-command-center-activation-20260907-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-titan-cloud-sell-scheduler-activation-20260907-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-kaggle-account-binding-exercised-20260907-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-github-repository-portfolio-live-expansion-20260907-03",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-github-repository-portfolio-live-expansion-20260907-02",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-github-repository-portfolio-privacy-refresh-20260907-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-upwork-marketplace-capacity-activation-20260902-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-business-pack-factory-activation-20260902-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-coil-pfc-host-toolchain-activation-20260902-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-connected-capability-fleet-activation-20260901-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-vercel-capacity-activation-20260901-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-agent-address-memory-liveness-activation-20260901-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-commons-skill-toolset-consumption-activation-20260901-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-github-repository-portfolio-activation-20260901-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-commons-data-corpus-alias-index-activation-20260831-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-discord-inbound-production-readback-20260831-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-discord-bridge-cloud-dark-correction-20260831-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-lm-gtm-agent-brief-floor-activation-20260831-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-lexington-mrf-diversion-gate-activation-20260831-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-source-parse-integrity-guard-activation-20260831-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-discord-bridge-production-activation-20260830-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-revenue-offer-stack-production-activation-20260830-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-opportunity-capability-registry-activation-20260830-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-internet-archive-mirror-activation-20260830-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-muhlnickel-distro-sales-door-activation-20260829-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-github-actions-watchdog-production-activation-20260829-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-supergrok-commons-tool-consumer-activation-20260828-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-github-actions-watchdog-advancement-20260828-01",
            raw.get("supersedes_source_ids") or [],
        )
        self.assertIn(
            "codex-grok-executor-queue-activation-20260828-01",
            raw.get("supersedes_source_ids") or [],
        )
        current_activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-titan-v5-day-close-animal-feed-certificate-resource-activation-20260912-01.json",
        )
        with open(current_activation_path, encoding="utf-8") as handle:
            current_activation = json.load(handle)
        self.assertEqual(current_activation["event_id"], catalog["source_id"])
        self.assertEqual(
            current_activation["event_type"], "RESOURCE_DISCOVERY_AND_ACTIVATION"
        )
        self.assertEqual(
            current_activation["selected_resource"],
            "titan-v5-day-close-animal-feed-certificate-authority",
        )
        self.assertEqual(current_activation["projection"]["resources"], 91)
        self.assertEqual(current_activation["projection"]["producing"], 63)
        self.assertEqual(current_activation["projection"]["inventory_records"], 53)
        self.assertEqual(current_activation["production_truth"]["source_pr"], 13379)
        self.assertEqual(
            current_activation["production_truth"]["source_merge_sha"],
            "eeabdb2c8ba75e40e5a3ee188fd2781d9e289fcb",
        )
        self.assertEqual(
            current_activation["production_truth"]["source_validation"]["alternate_feed_normal_passed"],
            25,
        )
        self.assertEqual(
            current_activation["production_truth"]["source_validation"]["alternate_feed_optimized_passed"],
            25,
        )
        self.assertEqual(
            current_activation["production_truth"]["source_validation"]["certificate_builder_normal_passed"],
            21,
        )
        self.assertEqual(
            current_activation["production_truth"]["source_validation"]["certificate_builder_optimized_passed"],
            21,
        )
        self.assertTrue(current_activation["production_truth"]["default_off"])
        self.assertEqual(current_activation["production_truth"]["new_full_games"], 0)
        self.assertEqual(current_activation["production_truth"]["candidate_promotions"], 0)
        self.assertEqual(
            current_activation["build_orders"][0]["commons_id"],
            "TITAN-V5-ANIMAL-CADENCE-MATCHED-EVAL-PACKAGE-20260912-01",
        )
        self.assertIn("p1789229352638719", current_activation["build_orders"][0]["permalink"])
        slack_cite = "p" + catalog["slack_ts"].replace(".", "")
        self.assertIn(slack_cite, current_activation["evidence"]["slack_claim"])
        activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-commons-data-corpus-alias-index-activation-20260831-01.json",
        )
        with open(activation_path, encoding="utf-8") as handle:
            activation = json.load(handle)
        self.assertEqual(
            activation["event_id"],
            "codex-commons-data-corpus-alias-index-activation-20260831-01",
        )
        self.assertEqual(activation["event_type"], "RESOURCE_ACTIVATION")
        self.assertEqual(activation["selected_resource"], "commons-data-corpus")
        watchdog_production_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-github-actions-watchdog-production-activation-20260829-01.json",
        )
        with open(watchdog_production_path, encoding="utf-8") as handle:
            watchdog_production = json.load(handle)
        self.assertEqual(
            watchdog_production["event_id"],
            "codex-github-actions-watchdog-production-activation-20260829-01",
        )
        self.assertEqual(watchdog_production["event_type"], "RESOURCE_ACTIVATION")
        self.assertEqual(watchdog_production["selected_resource"], "github-actions")
        self.assertIn(
            "p1787976347829539", watchdog_production["evidence"]["slack_start"]
        )
        watchdog_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-github-actions-watchdog-advancement-20260828-01.json",
        )
        with open(watchdog_path, encoding="utf-8") as handle:
            watchdog = json.load(handle)
        self.assertEqual(
            watchdog["event_id"],
            "codex-github-actions-watchdog-advancement-20260828-01",
        )
        self.assertIn("p1787933005065549", watchdog["evidence"]["slack"])
        self.assertNotEqual(catalog["slack_ts"], "1788304349.282199")
        self.assertNotEqual(catalog["slack_ts"], "1788300060.035449")
        self.assertNotEqual(catalog["slack_ts"], "1788256871.664259")
        self.assertNotEqual(catalog["slack_ts"], "1788105886.420729")
        self.assertNotEqual(catalog["slack_ts"], "1788083921.230169")
        self.assertNotEqual(catalog["slack_ts"], "1788062418.023819")
        self.assertNotEqual(catalog["slack_ts"], "1787997064.565089")
        self.assertNotEqual(catalog["slack_ts"], "1787976347.829539")
        self.assertNotEqual(catalog["slack_ts"], "1787954879.428259")
        self.assertNotEqual(catalog["slack_ts"], "1787933005.065549")
        superseded_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-grok-executor-queue-activation-20260828-01.json",
        )
        with open(superseded_path, encoding="utf-8") as handle:
            superseded = json.load(handle)
        self.assertEqual(
            superseded["connected_app_aggregate"]["slack_activation_ts"],
            "1787911777.379739",
        )
        self.assertNotEqual(
            catalog["slack_ts"],
            superseded["connected_app_aggregate"]["slack_activation_ts"],
        )
        rows = {row["name"]: row for row in catalog["surfaces"]}
        self.assertEqual(rows["supergrok-heavy"]["stage"], "PRODUCING")
        self.assertEqual(rows["supergrok-heavy"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["titan-v25-cloud-simulation-order-queue"]["stage"], "PRODUCING")
        self.assertEqual(rows["titan-v25-cloud-simulation-order-queue"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["titan-v25-cloud-simulation-order-queue"]["quantity"], 72)
        self.assertEqual(rows["titan-v25-joint-sell-planner"]["stage"], "PRODUCING")
        self.assertEqual(rows["titan-v25-joint-sell-planner"]["condition"], "CONSTRAINED")
        self.assertIn("EXACT_ARCHIVE_SOURCE_MANIFEST", rows["titan-v25-joint-sell-planner"]["authority"])
        self.assertIn("fb292c5c323335acc7a9e31fdaace590b6f3bff9767c5495f1406c5211e32f23", rows["titan-v25-joint-sell-planner"]["exact_safe_probe"])
        self.assertEqual(rows["titan-v5-worker-job-payback-certificate"]["stage"], "PRODUCING")
        self.assertEqual(rows["titan-v5-worker-job-payback-certificate"]["condition"], "CONSTRAINED")
        self.assertIn("EXACT_CALLER_CERTIFIED", rows["titan-v5-worker-job-payback-certificate"]["authority"])
        self.assertIn("e2965ae179ba734cc40fce9dc9c450a80e84ec2e", rows["titan-v5-worker-job-payback-certificate"]["exact_safe_probe"])
        self.assertEqual(rows["titan-v5-cross-evidence-promotion-gate"]["stage"], "PRODUCING")
        self.assertEqual(rows["titan-v5-cross-evidence-promotion-gate"]["condition"], "CONSTRAINED")
        self.assertIn("EXACT_MANIFEST_ENGAGEMENT_RUNTIME_IDENTITY", rows["titan-v5-cross-evidence-promotion-gate"]["authority"])
        self.assertIn("ea1e6419511bacad4560f88e77bbdafb300c7b4a", rows["titan-v5-cross-evidence-promotion-gate"]["exact_safe_probe"])
        self.assertEqual(rows["titan-v5-day-close-animal-feed-certificate-authority"]["stage"], "PRODUCING")
        self.assertEqual(rows["titan-v5-day-close-animal-feed-certificate-authority"]["condition"], "CONSTRAINED")
        self.assertIn("DEFAULT_OFF", rows["titan-v5-day-close-animal-feed-certificate-authority"]["authority"])
        self.assertIn("e7b7e7d0372e163c1b83e481d823a82a9fbedeab", rows["titan-v5-day-close-animal-feed-certificate-authority"]["exact_safe_probe"])
        self.assertIn("September 7 global reset", rows["gpt-6-astra-codex-carrier"]["next_action"])
        self.assertEqual(rows["google-ai-mode-browser-mesh"]["capacity"], "LIVE")
        self.assertEqual(rows["google-ai-mode-browser-mesh"]["stage"], "PRODUCING")
        self.assertEqual(rows["google-ai-mode-browser-mesh"]["condition"], "LIVE")
        self.assertEqual(rows["gemini-google-research-fleet"]["quantity"], 2)
        self.assertEqual(rows["gemini-google-research-fleet"]["stage"], "PRODUCING")
        self.assertEqual(rows["grokcom-triggered-automation-fleet"]["quantity"], 14)
        self.assertEqual(rows["grokcom-triggered-automation-fleet"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["google-spark-research-candidate"]["stage"], "DECLARED")
        self.assertEqual(rows["google-spark-research-candidate"]["capacity"], "UNMEASURED")
        self.assertEqual(rows["grokbot-pool-pair"]["quantity"], 2)
        self.assertEqual(rows["grokbot-pool-pair"]["condition"], "HELD")
        self.assertEqual(rows["github-actions"]["stage"], "PRODUCING")
        self.assertEqual(rows["github-actions"]["condition"], "DEGRADED")
        self.assertEqual(rows["muhlnickel-distro-public-sales-door"]["stage"], "PRODUCING")
        self.assertEqual(
            rows["muhlnickel-distro-public-sales-door"]["condition"], "CONSTRAINED"
        )
        self.assertEqual(rows["internet-archive-history-mirror"]["stage"], "PRODUCING")
        self.assertEqual(
            rows["internet-archive-history-mirror"]["condition"], "CONSTRAINED"
        )
        self.assertEqual(rows["opportunity-capability-registry"]["stage"], "PRODUCING")
        self.assertEqual(
            rows["opportunity-capability-registry"]["condition"], "CONSTRAINED"
        )
        self.assertEqual(rows["revenue-offer-stack"]["stage"], "PRODUCING")
        self.assertEqual(rows["revenue-offer-stack"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["discord-bridge"]["stage"], "PRODUCING")
        self.assertEqual(rows["discord-bridge"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["source-parse-integrity-guard"]["stage"], "PRODUCING")
        self.assertEqual(rows["source-parse-integrity-guard"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["lexington-mrf-diversion-gate"]["stage"], "PRODUCING")
        self.assertEqual(rows["lexington-mrf-diversion-gate"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["lm-gtm-agent-brief-floor"]["stage"], "PRODUCING")
        self.assertEqual(rows["lm-gtm-agent-brief-floor"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["coil-pfc-host-toolchain"]["stage"], "PRODUCING")
        self.assertEqual(rows["coil-pfc-host-toolchain"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["commons-business-pack-factory"]["stage"], "PRODUCING")
        self.assertEqual(rows["commons-business-pack-factory"]["condition"], "CONSTRAINED")
        self.assertIn("NOT_MINTED", rows["commons-business-pack-factory"]["rate_plan_boundary"])
        self.assertEqual(activation["after"]["stage"], "PRODUCING")
        self.assertEqual(activation["after"]["condition"], "CONSTRAINED")
        self.assertEqual(activation["projection"]["resources"], 66)
        self.assertEqual(activation["projection"]["producing"], 35)
        self.assertEqual(activation["counts"]["duplicate_groups"], 504)
        self.assertEqual(activation["counts"]["extra_alias_paths"], 1232)
        self.assertEqual(activation["counts"]["deletions"], 0)
        self.assertEqual(activation["counts"]["history_rewrites"], 0)
        self.assertEqual(activation["counts"]["blob_content_copies"], 0)
        self.assertIn(
            "inventory/resources/records/codex-commons-data-corpus-alias-index-activation-20260831-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-discord-inbound-production-readback-20260831-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-discord-bridge-cloud-dark-correction-20260831-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-lm-gtm-agent-brief-floor-activation-20260831-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-lexington-mrf-diversion-gate-activation-20260831-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-source-parse-integrity-guard-activation-20260831-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-discord-bridge-production-activation-20260830-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-revenue-offer-stack-production-activation-20260830-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-opportunity-capability-registry-activation-20260830-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-internet-archive-mirror-activation-20260830-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-muhlnickel-distro-sales-door-activation-20260829-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-github-actions-watchdog-production-activation-20260829-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-commons-skill-toolset-consumption-activation-20260901-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-vercel-capacity-activation-20260901-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-connected-capability-fleet-activation-20260901-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-resource-master-delta-engine-activation-20260901-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-google-research-grok-automation-resource-delta-20260902-01.json",
            raw.get("record_sources") or [],
        )
        self.assertIn(
            "inventory/resources/records/codex-titan-official-engine-benchmark-evidence-activation-20260909-01.json",
            raw.get("record_sources") or [],
        )
        self.assertFalse(catalog["cache_as_capacity"])
        self.assertFalse(catalog["secrets"])
        names = [row["name"] for row in catalog["surfaces"]]
        self.assertIn("github", names)
        self.assertIn("huggingface", names)
        self.assertIn("vercel", names)
        self.assertIn("chatgpt-connected-capability-fleet", names)
        for row in catalog["surfaces"]:
            if row["capacity"] == "LIVE":
                for field in REQUIRED_FIELDS:
                    self.assertTrue(row[field], field)
        self.assertFalse(json_has_secret_key(text))
        receipt = catalog_from_row({"live": ["github"], "not_verified": ["huggingface"]})
        self.assertFalse(receipt["secrets"])
        self.assertFalse(receipt["cache_as_capacity"])
        self.assertEqual(receipt["titan"], "NOT_WRITTEN")

    def test_v2_catalog_covers_the_whole_resource_lifecycle(self):
        catalog_path = os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["schema"], "commons-resource-ledger/v2")
        self.assertEqual(tuple(catalog["stage_order"]), RESOURCE_STAGES)
        self.assertGreaterEqual(len(catalog["surfaces"]), 40)
        self.assertGreaterEqual(len({row["kind"] for row in catalog["surfaces"]}), 12)
        for row in catalog["surfaces"]:
            for field in V2_REQUIRED_FIELDS:
                self.assertTrue(row[field], "%s.%s" % (row["name"], field))
            self.assertIn(row["stage"], RESOURCE_STAGES)
            self.assertIn(row["condition"], RESOURCE_CONDITIONS)

        measured = measure_from_rows(catalog)
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        self.assertGreaterEqual(measured["producing_count"], 10)
        queue_names = [row["name"] for row in measured["activation_queue"]]
        self.assertNotIn("titan-hands-windows", queue_names)
        self.assertIn("titan-hands-windows", measured["expired_resources"])
        self.assertNotIn("github-actions", queue_names)
        self.assertEqual(measured["activation_queue"][0]["name"], "upwork-marketplace-account")
        self.assertEqual(measured["activation_queue"][0]["priority"], 70)
        self.assertIn("outcome-commerce-bridge", measured["expired_resources"])
        self.assertNotIn("commons-skill-and-tool-set", queue_names)
        self.assertNotIn("chatgpt-connected-capability-fleet", queue_names)
        self.assertNotIn("resource-master-office", queue_names)
        skills = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "commons-skill-and-tool-set"
        )
        self.assertEqual(skills["stage"], "PRODUCING")
        self.assertEqual(
            skills["last_receipt"],
            "codex-commons-skill-toolset-consumption-activation-20260901-01",
        )
        fleet = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "chatgpt-connected-capability-fleet"
        )
        self.assertEqual(fleet["stage"], "PRODUCING")
        self.assertEqual(
            fleet["last_receipt"],
            "codex-github-repository-portfolio-live-expansion-20260907-02",
        )
        office = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "resource-master-office"
        )
        self.assertEqual(office["stage"], "PRODUCING")
        self.assertEqual(
            office["last_receipt"],
            "codex-resource-master-delta-engine-activation-20260901-01",
        )
        upwork = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "upwork-marketplace-account"
        )
        self.assertEqual(upwork["stage"], "REACHABLE")
        self.assertEqual(upwork["condition"], "CONSTRAINED")
        self.assertEqual(
            upwork["last_receipt"],
            "codex-upwork-marketplace-capacity-activation-20260902-01",
        )
        kaggle = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "kaggle-account-binding"
        )
        self.assertEqual(kaggle["stage"], "PRODUCING")
        self.assertEqual(kaggle["condition"], "CONSTRAINED")
        self.assertEqual(
            kaggle["last_receipt"],
            "codex-kaggle-account-binding-exercised-20260907-01",
        )
        sell = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "titan-cloud-sell-scheduler"
        )
        self.assertEqual(sell["capacity"], "LIVE")
        self.assertEqual(sell["stage"], "PRODUCING")
        self.assertEqual(sell["condition"], "CONSTRAINED")
        self.assertEqual(
            sell["last_receipt"],
            "codex-titan-cloud-sell-scheduler-activation-20260907-01",
        )
        self.assertIn("NO_KAGGLE_PROVIDER_WRITE", sell["authority"])
        self.assertIn(
            "32c8610c9827d1686a6f831e2c4b6af4c00d32d2aa04dcf25699d976d6d97dd9",
            sell["exact_safe_probe"],
        )
        command_center = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "commons-operation-command-center"
        )
        self.assertEqual(command_center["capacity"], "LIVE")
        self.assertEqual(command_center["stage"], "PRODUCING")
        self.assertEqual(command_center["condition"], "CONSTRAINED")
        self.assertEqual(
            command_center["last_receipt"],
            "codex-commons-operation-command-center-activation-20260907-01",
        )
        self.assertIn("STABLE_OPERATION_ID", command_center["authority"])
        self.assertIn("NO_CREDENTIAL_VALUE_DISPLAY", command_center["authority"])
        self.assertIn("eight command_center_* tools", command_center["value"])
        model_lab = next(
            row for row in catalog["surfaces"] if row["name"] == "titan-cloud-model-lab"
        )
        self.assertEqual(model_lab["capacity"], "LIVE")
        self.assertEqual(model_lab["stage"], "PRODUCING")
        self.assertEqual(model_lab["condition"], "CONSTRAINED")
        self.assertEqual(
            model_lab["last_receipt"],
            "codex-titan-cloud-model-lab-activation-20260908-01",
        )
        self.assertIn("ONE_POLICY_INSTANCE_PER_ACTOR_MATCH", model_lab["authority"])
        self.assertIn("NO_KAGGLE_PROVIDER_WRITE", model_lab["authority"])
        self.assertIn("4f1a541c4145ddf0b3cdb73919b44001e9baebdb", model_lab["exact_safe_probe"])
        self.assertIn("d65a9ba738f2674fe4be343126d40c4debf03a8e5a44019d67135cbbcaacb11e", model_lab["exact_safe_probe"])
        profiler = next(
            row for row in catalog["surfaces"] if row["name"] == "titan-runtime-profiler"
        )
        self.assertEqual(profiler["capacity"], "LIVE")
        self.assertEqual(profiler["stage"], "PRODUCING")
        self.assertEqual(profiler["condition"], "CONSTRAINED")
        self.assertEqual(
            profiler["last_receipt"],
            "codex-titan-runtime-profiler-activation-20260908-01",
        )
        self.assertIn("NO_ENGINE_ADVANCE", profiler["authority"])
        self.assertIn("NO_PROVIDER_OR_KAGGLE_WRITE", profiler["authority"])
        self.assertIn("8ae01c736bd44ffc424f91f657c2861126115d24", profiler["exact_safe_probe"])
        self.assertIn("0f7b1cacba615b614ae2b93833c53a87bd6567df", profiler["exact_safe_probe"])
        astra = next(
            row for row in catalog["surfaces"] if row["name"] == "gpt-6-astra-codex-carrier"
        )
        self.assertEqual(astra["capacity"], "LIVE")
        self.assertEqual(astra["stage"], "PRODUCING")
        self.assertEqual(astra["condition"], "CONSTRAINED")
        self.assertEqual(
            astra["last_receipt"],
            "codex-gpt-6-astra-carrier-activation-20260908-01",
        )
        self.assertIn("NO_QUOTA_OR_GLOBAL_AVAILABILITY_INFERENCE", astra["authority"])
        self.assertIn("06616531b56ec4dfcc421bce82db8f8e04091b15", astra["exact_safe_probe"])
        self.assertIn("c3ddcb017d5b1ad53f2bf08d6efe2986cc6ac3a9", astra["exact_safe_probe"])
        trade_quote = next(
            row for row in catalog["surfaces"] if row["name"] == "hive-trade-quote-schedule"
        )
        self.assertEqual(trade_quote["capacity"], "LIVE")
        self.assertEqual(trade_quote["stage"], "PRODUCING")
        self.assertEqual(trade_quote["condition"], "CONSTRAINED")
        self.assertEqual(
            trade_quote["last_receipt"],
            "codex-hive-trade-quote-schedule-activation-20260908-01",
        )
        self.assertIn("NO_GUESSED_MEASUREMENTS", trade_quote["authority"])
        self.assertIn("NO_OUTREACH_PAYMENT_OR_EXTERNAL_CALENDAR_WRITE", trade_quote["authority"])
        self.assertIn("a75dae6308ce4bab3e0b2625638c953ee2d25dcd", trade_quote["exact_safe_probe"])
        self.assertIn("fd3d56b6dad06c1177795ec92e1916fb24aa6955", trade_quote["exact_safe_probe"])
        intake_crm = next(
            row for row in catalog["surfaces"] if row["name"] == "hive-intake-crm-workflow"
        )
        self.assertEqual(intake_crm["capacity"], "LIVE")
        self.assertEqual(intake_crm["stage"], "PRODUCING")
        self.assertEqual(intake_crm["condition"], "CONSTRAINED")
        self.assertEqual(
            intake_crm["last_receipt"],
            "codex-hive-intake-crm-workflow-activation-20260909-01",
        )
        self.assertIn("PRIVATE_SINGLE_WORKSPACE_OPERATION_ONLY", intake_crm["authority"])
        self.assertIn("NO_CUSTOMER_PROVIDER_CREDENTIAL", intake_crm["authority"])
        self.assertIn("376e4858700d09541e11308bbcb0194427f931fc", intake_crm["exact_safe_probe"])
        self.assertIn("da339d714fd610689dafaca5a2e47c57d772edce", intake_crm["exact_safe_probe"])
        human_validator = next(
            row for row in catalog["surfaces"]
            if row["name"] == "human-outcomes-input-validator"
        )
        self.assertEqual(human_validator["capacity"], "LIVE")
        self.assertEqual(human_validator["stage"], "PRODUCING")
        self.assertEqual(human_validator["condition"], "CONSTRAINED")
        self.assertEqual(
            human_validator["last_receipt"],
            "codex-human-outcomes-input-validator-activation-20260909-01",
        )
        self.assertIn("READ_ONLY_INPUT_MEASUREMENT", human_validator["authority"])
        self.assertIn("NO_CUSTOMER_PROVIDER_CHECKOUT", human_validator["authority"])
        self.assertIn(
            "2dbb743400f5035fb999c06da4d5f0c7fb5c26e7",
            human_validator["exact_safe_probe"],
        )
        self.assertIn(
            "bef953d9caea4210d92a23a46fdbd30ab2322c04",
            human_validator["exact_safe_probe"],
        )
        benchmark = next(
            row
            for row in catalog["surfaces"]
            if row["name"] == "titan-official-engine-benchmark-evidence"
        )
        self.assertEqual(benchmark["capacity"], "LIVE")
        self.assertEqual(benchmark["stage"], "PRODUCING")
        self.assertEqual(benchmark["condition"], "CONSTRAINED")
        self.assertEqual(
            benchmark["last_receipt"],
            "codex-titan-official-engine-benchmark-evidence-activation-20260909-01",
        )
        self.assertIn("EXACT_ENGINE_SOURCE_ARCHIVE_SEED_AND_SEAT_BINDING", benchmark["authority"])
        self.assertIn("PRIVATE_RAW_BUNDLE_STAYS_PRIVATE", benchmark["authority"])
        self.assertIn("NO_GAME_RERUN_OR_KAGGLE_PROVIDER_WRITE", benchmark["authority"])
        self.assertIn(
            "faeb4338e5ec8bd0d53fe6f3a4e8fda9847183be",
            benchmark["exact_safe_probe"],
        )
        self.assertIn(
            "f55e5aaf49c57f47314a77087204615cf5aa78ed",
            benchmark["exact_safe_probe"],
        )
        self.assertEqual(
            [row["priority"] for row in measured["activation_queue"]],
            sorted((row["priority"] for row in measured["activation_queue"]), reverse=True),
        )
        self.assertIn("commons-swarm-gateway", measured["expired_resources"])
        self.assertIn("stale-claim-capacity", measured["expired_resources"])
        self.assertEqual(
            sum(measured["freshness_counts"].values()),
            measured["resource_count"],
        )
        self.assertTrue(set(measured["freshness_counts"]).issubset(RESOURCE_FRESHNESS_STATES))

    def test_titan_official_benchmark_activation_binds_exact_completed_panel(self):
        activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-titan-official-engine-benchmark-evidence-activation-20260909-01.json",
        )
        with open(activation_path, encoding="utf-8") as handle:
            activation = json.load(handle)
        truth = activation["production_truth"]
        self.assertEqual(
            truth["operation_id"],
            "titan-official-fullgame-6705-v1-20260909-01",
        )
        self.assertEqual(truth["source_pr"], 11005)
        self.assertEqual(truth["exact_games"], 128)
        self.assertEqual(truth["completed"], 128)
        self.assertEqual(truth["errors"], 0)
        self.assertEqual(truth["timeouts"], 0)
        self.assertEqual(truth["current_v2"]["games"], 80)
        self.assertEqual(truth["current_v2"]["losses"], 0)
        self.assertEqual(truth["current_v2_vs_submitted_v1"]["wins"], 16)
        self.assertEqual(activation["projection"]["resources"], 86)
        self.assertEqual(activation["projection"]["producing"], 58)
        self.assertIn("hosted score", activation["verification"]["zero_fabrication"])
        self.assertIn("does not copy", truth["private_bundle"])

    def test_titan_joint_sell_activation_binds_current_package_without_game_claim(self):
        activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-titan-v25-joint-sell-resource-activation-20260909-01.json",
        )
        with open(activation_path, encoding="utf-8") as handle:
            activation = json.load(handle)
        truth = activation["production_truth"]
        self.assertEqual(truth["source_head_sha"], "d9636fe6af454b667c0b6fb96e6faf1402d74010")
        self.assertEqual(truth["source_merge_sha"], "596a5cd9987bf8aadee17387f581dcc8813b30d0")
        self.assertEqual(truth["archive_bytes"], 401937)
        self.assertEqual(truth["archive_runtime_files"], 103)
        self.assertEqual(truth["archive_validation"]["runtime_member_hashes_verified"], 103)
        self.assertEqual(truth["playing_strength_for_changed_bytes"], "NOT_MEASURED")
        self.assertEqual(activation["build_orders"], [])
        self.assertIn("hosted score", activation["verification"]["zero_fabrication"])

    def test_producing_github_actions_leaves_activation_queue(self):
        catalog_path = os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        rows = {row["name"]: row for row in catalog["surfaces"]}
        self.assertEqual(rows["github-actions"]["stage"], "PRODUCING")
        self.assertEqual(rows["github-actions"]["condition"], "DEGRADED")
        self.assertEqual(
            rows["github-actions"]["last_receipt"],
            "codex-github-actions-watchdog-production-activation-20260829-01",
        )
        live_queue = [
            row["name"] for row in measure_from_rows(catalog)["activation_queue"]
        ]
        self.assertNotIn("github-actions", live_queue)

        exercised = {
            **LIVE_FIELDS,
            "name": "github-actions",
            "kind": "COMPUTE",
            "capacity": "LIVE",
            "stage": "EXERCISED",
            "condition": "DEGRADED",
            "consumer": "watchdog",
            "value": "ticks",
            "next_action": "observe one post-repair tick",
            "source": "fixture",
            "holder": "Commons",
            "authority": "SAFE",
            "last_used_at": "2026-08-29T03:57:19Z",
            "stale_after": "next terminal watchdog result",
            "priority": 85,
        }
        producing = dict(exercised, stage="PRODUCING", priority=70)
        facts = {
            "schema": "commons-resource-ledger/v2",
            "snapshot": {"observed_at": "2026-08-29T04:05:47Z"},
        }
        queued = measure_from_rows({**facts, "surfaces": [exercised]})
        unqueued = measure_from_rows({**facts, "surfaces": [producing]})
        self.assertEqual([row["name"] for row in queued["activation_queue"]], ["github-actions"])
        self.assertEqual(queued["activation_queue"][0]["priority"], 85)
        self.assertEqual([row["name"] for row in unqueued["activation_queue"]], [])

    def test_muhlnickel_distro_sales_door_is_producing_without_cash(self):
        catalog_path = os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        rows = {row["name"]: row for row in catalog["surfaces"]}
        door = rows["muhlnickel-distro-public-sales-door"]
        self.assertEqual(door["capacity"], "LIVE")
        self.assertEqual(door["stage"], "PRODUCING")
        self.assertEqual(door["condition"], "CONSTRAINED")
        self.assertEqual(
            door["last_receipt"],
            "codex-muhlnickel-distro-sales-door-activation-20260829-01",
        )
        self.assertIn("not checkout", door["rate_plan_boundary"].lower())
        live_queue = [
            row["name"] for row in measure_from_rows(catalog)["activation_queue"]
        ]
        self.assertNotIn("muhlnickel-distro-public-sales-door", live_queue)

        activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-muhlnickel-distro-sales-door-activation-20260829-01.json",
        )
        with open(activation_path, encoding="utf-8") as handle:
            activation = json.load(handle)
        self.assertEqual(
            activation["event_type"], "RESOURCE_DISCOVERY_AND_ACTIVATION"
        )
        self.assertEqual(
            activation["selected_resource"], "muhlnickel-distro-public-sales-door"
        )
        self.assertEqual(activation["after"]["capacity"], "LIVE")
        self.assertEqual(activation["after"]["stage"], "PRODUCING")
        self.assertEqual(activation["after"]["condition"], "CONSTRAINED")
        self.assertEqual(activation["projection"]["resources"], 61)
        self.assertEqual(activation["projection"]["producing"], 27)
        self.assertIn(
            "No dedicated DISTRO Payment Link or checkout", activation["non_claims"]
        )
        self.assertIn(
            "No buyer inquiry, order, acceptance, payment, settlement, payout, revenue, or cash",
            activation["non_claims"],
        )

    def test_internet_archive_history_mirror_is_producing_without_canonical_claim(self):
        catalog_path = os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        rows = {row["name"]: row for row in catalog["surfaces"]}
        mirror = rows["internet-archive-history-mirror"]
        self.assertEqual(mirror["capacity"], "LIVE")
        self.assertEqual(mirror["stage"], "PRODUCING")
        self.assertEqual(mirror["condition"], "CONSTRAINED")
        self.assertEqual(
            mirror["last_receipt"],
            "unseated-dir9-snapshot-ia-ready-20260830-01",
        )
        self.assertIn("not git head", mirror["rate_plan_boundary"].lower())
        self.assertIn("public_read", mirror["authority"].lower())
        live_queue = [
            row["name"] for row in measure_from_rows(catalog)["activation_queue"]
        ]
        self.assertNotIn("internet-archive-history-mirror", live_queue)

        activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-internet-archive-mirror-activation-20260830-01.json",
        )
        with open(activation_path, encoding="utf-8") as handle:
            activation = json.load(handle)
        self.assertEqual(
            activation["event_type"], "RESOURCE_DISCOVERY_AND_ACTIVATION"
        )
        self.assertEqual(
            activation["selected_resource"], "internet-archive-history-mirror"
        )
        self.assertEqual(activation["after"]["capacity"], "LIVE")
        self.assertEqual(activation["after"]["stage"], "PRODUCING")
        self.assertEqual(activation["after"]["condition"], "CONSTRAINED")
        self.assertEqual(activation["projection"]["resources"], 62)
        self.assertEqual(activation["projection"]["producing"], 28)
        self.assertIn(
            "No archive write or provider token spend by this activation",
            activation["non_claims"],
        )
        self.assertIn(
            "No canonical current-main durability through Internet Archive",
            activation["non_claims"],
        )
        self.assertIn(
            "No deployment, device actuation, payment, settlement, payout, revenue, or cash",
            activation["non_claims"],
        )
        self.assertIn("NO_AUTH", activation["authority"])
        self.assertIn("no login", activation["verification"]["open_door_contract"].lower())

    def test_revenue_offer_stack_is_producing_without_cash(self):
        catalog_path = os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json")
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        rows = {row["name"]: row for row in catalog["surfaces"]}
        stack = rows["revenue-offer-stack"]
        self.assertEqual(stack["capacity"], "LIVE")
        self.assertEqual(stack["stage"], "PRODUCING")
        self.assertEqual(stack["condition"], "CONSTRAINED")
        self.assertEqual(
            stack["last_receipt"],
            "codex-revenue-offer-stack-production-activation-20260830-01",
        )
        self.assertIn("not a buyer", stack["rate_plan_boundary"].lower())
        self.assertIn("cash remains usd 0", stack["rate_plan_boundary"].lower())
        live_queue = [
            row["name"] for row in measure_from_rows(catalog)["activation_queue"]
        ]
        self.assertNotIn("revenue-offer-stack", live_queue)
        measured = measure_from_rows(catalog)

        activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-revenue-offer-stack-production-activation-20260830-01.json",
        )
        with open(activation_path, encoding="utf-8") as handle:
            activation = json.load(handle)
        self.assertEqual(
            activation["event_type"], "RESOURCE_LIFECYCLE_ADVANCEMENT"
        )
        self.assertEqual(activation["selected_resource"], "revenue-offer-stack")
        self.assertEqual(activation["after"]["capacity"], "LIVE")
        self.assertEqual(activation["after"]["stage"], "PRODUCING")
        self.assertEqual(activation["after"]["condition"], "CONSTRAINED")
        self.assertEqual(activation["before"]["stage"], "EXERCISED")
        self.assertEqual(activation["projection"]["resources"], 63)
        self.assertEqual(activation["projection"]["producing"], 30)
        self.assertGreaterEqual(
            measured["resource_count"], activation["projection"]["resources"]
        )
        self.assertGreaterEqual(
            measured["producing_count"], activation["projection"]["producing"]
        )
        self.assertEqual(activation["counts"]["cash_received_usd"], 0)
        self.assertEqual(activation["counts"]["completed_checkout_sessions"], 0)
        self.assertEqual(activation["counts"]["public_buyer_intent_doors"], 4)
        self.assertIn(
            "No buyer, checkout completion, scope acceptance, authorization, capture, settlement, payout, bank availability, revenue, or cash",
            activation["non_claims"],
        )
        self.assertIn("p1788105886420729", activation["evidence"]["slack_claim"])
        self.assertIn("without commons login", activation["verification"]["public_road_truth"].lower())
        self.assertIn("login wall", activation["verification"]["secrets_and_open_door"].lower())
        self.assertIn("no credentials", activation["verification"]["secrets_and_open_door"].lower())

    def test_duration_freshness_expires_claims_without_rewriting_condition(self):
        row = {
            **LIVE_FIELDS,
            "name": "claimed-capacity",
            "capacity": "LIVE",
            "kind": "WORK_QUEUE",
            "stage": "ASSIGNED",
            "condition": "ACTIVE_UNKNOWN",
            "consumer": "one exact job",
            "value": "reserved capacity",
            "next_action": "release when stale",
            "source": "receipt",
            "holder": "worker",
            "authority": "bounded claim",
            "last_used_at": "2026-08-26T12:00:00Z",
            "stale_after": "PT6H",
            "evidence_ts": "2026-08-26T12:00:00Z",
            "priority": 100,
        }
        self.assertEqual(evidence_freshness(row, "2026-08-26T18:00:00Z"), "FRESH")
        self.assertEqual(evidence_freshness(row, "2026-08-26T18:00:01Z"), "STALE")
        measured = measure_from_rows(
            {
                "schema": "commons-resource-ledger/v2",
                "snapshot": {"observed_at": "2026-08-26T18:00:01Z"},
                "surfaces": [row],
            }
        )
        self.assertEqual(measured["surfaces"][0]["condition"], "ACTIVE_UNKNOWN")
        self.assertFalse(measured["surfaces"][0]["claim_active"])
        self.assertEqual(measured["expired_resources"], ["claimed-capacity"])
        self.assertEqual(measured["activation_queue"], [])

    def test_owner_and_holds_are_resources_not_capacity_inferences(self):
        with open(os.path.join(ROOT, "ground", "RESOURCE_LEDGER.json"), encoding="utf-8") as handle:
            rows = {row["name"]: row for row in load_catalog(handle.read())["surfaces"]}
        self.assertEqual(rows["bryce-owner-operator"]["kind"], "HUMAN")
        self.assertEqual(rows["bryce-owner-operator"]["stage"], "PRODUCING")
        self.assertEqual(rows["cursor-ultra"]["capacity"], "LIVE")
        self.assertEqual(rows["cursor-ultra"]["stage"], "PRODUCING")
        self.assertEqual(rows["cursor-ultra"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["claude"]["condition"], "HELD")
        self.assertIn("owner-handled", rows["claude"]["assigned_backlog"].lower())
        self.assertEqual(rows["titan-hands-windows"]["stage"], "EXERCISED")
        self.assertEqual(rows["owner-workstation"]["capacity"], "NOT_VERIFIED")
        self.assertEqual(rows["owner-workstation"]["condition"], "BLOCKED")
        self.assertEqual(rows["public-commerce-road"]["stage"], "PRODUCING")
        self.assertEqual(rows["public-commerce-road"]["condition"], "CONSTRAINED")
        self.assertEqual(rows["openai-automation-fleet"]["quantity"], 7)
        self.assertEqual(rows["kite-task-forge-r0"]["stage"], "PRODUCING")
        self.assertEqual(rows["kite-task-forge-r0"]["condition"], "LIVE")
        self.assertEqual(rows["commons-network-plugin"]["stage"], "PRODUCING")
        self.assertEqual(rows["stripe-sandbox-account"]["stage"], "REACHABLE")
        self.assertEqual(rows["stripe-sandbox-account"]["condition"], "CONSTRAINED")

    def test_append_only_census_and_human_doors_exist(self):
        record_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-master-resource-census-20260826-01.json",
        )
        with open(record_path, encoding="utf-8") as handle:
            record_text = handle.read()
        self.assertFalse(json_has_secret_key(record_text))
        self.assertIn('"event_type": "MASTER_CENSUS"', record_text)
        with open(os.path.join(ROOT, "resources.html"), encoding="utf-8") as handle:
            resources_html = handle.read()
        with open(os.path.join(ROOT, "ledger.html"), encoding="utf-8") as handle:
            ledger_html = handle.read()
        self.assertIn('href="./ledger.html"', resources_html)
        self.assertIn("bryce-owner-operator", ledger_html)
        self.assertIn("stage-filter", ledger_html)

        activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-resource-master-office-activation-20260826-01.json",
        )
        with open(activation_path, encoding="utf-8") as handle:
            activation = json.load(handle)
        self.assertEqual(activation["event_type"], "RESOURCE_ACTIVATION")
        self.assertEqual(activation["selected_resource"], "resource-master-office")
        self.assertEqual(
            activation["after"]["integration_main_sha"],
            "2423415c754b13ce2d723ce9d85c4f9af802d4fb",
        )

        commerce_activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-public-commerce-road-activation-20260827-01.json",
        )
        with open(commerce_activation_path, encoding="utf-8") as handle:
            commerce_activation = json.load(handle)
        self.assertEqual(commerce_activation["event_type"], "RESOURCE_ACTIVATION")
        self.assertEqual(commerce_activation["selected_resource"], "public-commerce-road")
        self.assertEqual(commerce_activation["current_truth"]["collected_cash_usd"], "0.00")

        task_forge_activation_path = os.path.join(
            ROOT,
            "inventory",
            "resources",
            "records",
            "codex-kite-task-forge-activation-20260827-01.json",
        )
        with open(task_forge_activation_path, encoding="utf-8") as handle:
            task_forge_activation = json.load(handle)
        self.assertEqual(task_forge_activation["event_type"], "RESOURCE_ACTIVATION")
        self.assertEqual(task_forge_activation["selected_resource"], "kite-task-forge-r0")
        self.assertEqual(task_forge_activation["after"]["stage"], "PRODUCING")
        self.assertEqual(task_forge_activation["artifact_truth"]["records"], 32)
        self.assertEqual(task_forge_activation["projection"]["resources"], 56)
        self.assertEqual(task_forge_activation["connected_app_aggregate"]["stripe_livemode_accounts"], 0)

    def test_local_probes_see_absent_hf(self):
        probes = local_probes(
            os.path.join(ROOT, "does-not-exist-home"),
            which=lambda _name: None,
        )
        self.assertEqual(probes["hf_token_files"], [])
        self.assertFalse(probes["hf_cli"])

    def test_local_probes_do_not_turn_a_missing_home_into_a_fake_cli_zero(self):
        probes = local_probes(
            os.path.join(ROOT, "does-not-exist-home"),
            which=lambda name: "C:/tools/hf.exe" if name == "hf" else None,
        )
        self.assertTrue(probes["hf_cli"])

    def test_live_tree_measures(self):
        measured = measure_root(ROOT)
        self.assertTrue(measured["measured"])
        self.assertIn("github", measured["live"])
        self.assertIn("huggingface", measured["not_verified"])
        self.assertNotIn("huggingface", measured["live"])
        self.assertFalse(measured["cache_as_capacity"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        self.assertFalse(measured["secrets"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")


def json_has_secret_key(text):
    lowered = str(text or "").lower()
    needles = ("api_key", "password=", "authorization: ", "@gmail.com")
    return any(needle in lowered for needle in needles) or bool(
        re.search(r"(?<![a-z0-9])sk-[a-z0-9]{12,}", lowered)
    )


if __name__ == "__main__":
    unittest.main()
