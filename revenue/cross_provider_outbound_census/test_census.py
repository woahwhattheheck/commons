from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.cross_provider_outbound_census.census import CensusError, compile_census, verify_census

NOW = "2026-09-14T03:30:00Z"
H = lambda c: c * 64


def base():
    return {
        "schema": "commons-cross-provider-outbound-census/input-v1",
        "lease_input": {
            "schema": "outbound-connector-lease/v1",
            "buyer_scope": "elyanlabs.example",
            "opportunity": {
                "kind": "external",
                "authority": "github.com",
                "id": "scottcjn/rustchain-bounties/issues/16863",
            },
        },
        "intent": {
            "provider": "github",
            "route_sha256": H("a"),
            "claimant_scope": "solforge-z",
            "claim_scope": "claim-16863",
            "requested_at": "2026-09-14T03:29:50Z",
        },
        "aliases": [
            {"provider": "github", "route_sha256": H("a")},
            {"provider": "gmail", "route_sha256": H("b")},
        ],
        "snapshots": [
            {
                "provider": "github",
                "status": "COMPLETE",
                "observed_at": "2026-09-14T03:29:55Z",
                "query_sha256": H("c"),
                "covered_routes": [H("a")],
                "events": [],
            },
            {
                "provider": "gmail",
                "status": "COMPLETE",
                "observed_at": "2026-09-14T03:29:56Z",
                "query_sha256": H("d"),
                "covered_routes": [H("b")],
                "events": [],
            },
        ],
    }


def event(kind, *, route=None, at="2026-09-14T03:20:00Z", evidence=None):
    return {
        "route_sha256": route or H("b"),
        "event": kind,
        "event_at": at,
        "evidence_sha256": evidence or H("e"),
    }


class TestCensus(unittest.TestCase):
    def test_clean_requires_all_fallback_providers(self):
        p = compile_census(base(), trusted_now=NOW)
        self.assertEqual(p["decision"], "CLEAR_FOR_DOWNSTREAM_GATES")
        self.assertFalse(p["authority"]["external_send_authorized"])
        self.assertEqual(p["summary"]["required_providers"], ["github", "gmail"])

    def test_16863_class_missing_gmail_census_holds(self):
        x = base(); x["snapshots"] = x["snapshots"][:1]
        p = compile_census(x, trusted_now=NOW)
        self.assertEqual(p["decision"], "HOLD")
        self.assertIn("PROVIDER_CENSUS_MISSING:gmail", p["reasons"])

    def test_prior_email_fallback_send_blocks_github_retry(self):
        x = base(); x["snapshots"][1]["events"] = [event("PROVIDER_SENT")]
        p = compile_census(x, trusted_now=NOW)
        self.assertIn("PRIOR_PROVIDER_TOUCH_PRESENT", p["reasons"])
        self.assertEqual(p["evidence"][0]["provider"], "gmail")

    def test_human_reply_blocks(self):
        x = base(); x["snapshots"][1]["events"] = [event("HUMAN_REPLY")]
        self.assertIn("PRIOR_PROVIDER_TOUCH_PRESENT", compile_census(x, trusted_now=NOW)["reasons"])

    def test_auto_reply_blocks(self):
        x = base(); x["snapshots"][1]["events"] = [event("AUTO_REPLY")]
        self.assertIn("PRIOR_PROVIDER_TOUCH_PRESENT", compile_census(x, trusted_now=NOW)["reasons"])

    def test_unsubscribe_is_suppression(self):
        x = base(); x["snapshots"][1]["events"] = [event("UNSUBSCRIBE")]
        self.assertIn("SUPPRESSION_HISTORY_PRESENT", compile_census(x, trusted_now=NOW)["reasons"])

    def test_dnr_is_suppression(self):
        x = base(); x["snapshots"][1]["events"] = [event("DNR")]
        self.assertIn("SUPPRESSION_HISTORY_PRESENT", compile_census(x, trusted_now=NOW)["reasons"])

    def test_hard_bounce_requires_route_repair_not_rejection(self):
        x = base(); x["snapshots"][1]["events"] = [event("HARD_BOUNCE")]
        p = compile_census(x, trusted_now=NOW)
        self.assertIn("ROUTE_REPAIR_REQUIRED", p["reasons"])
        self.assertNotIn("SUPPRESSION_HISTORY_PRESENT", p["reasons"])

    def test_soft_bounce_requires_route_repair(self):
        x = base(); x["snapshots"][1]["events"] = [event("SOFT_BOUNCE")]
        self.assertIn("ROUTE_REPAIR_REQUIRED", compile_census(x, trusted_now=NOW)["reasons"])

    def test_provider_rejected_requires_route_repair(self):
        x = base(); x["snapshots"][1]["events"] = [event("PROVIDER_REJECTED")]
        self.assertIn("ROUTE_REPAIR_REQUIRED", compile_census(x, trusted_now=NOW)["reasons"])

    def test_ambiguous_effect_holds(self):
        x = base(); x["snapshots"][1]["events"] = [event("AMBIGUOUS_EFFECT")]
        self.assertIn("AMBIGUOUS_PROVIDER_EFFECT_PRESENT", compile_census(x, trusted_now=NOW)["reasons"])

    def test_throttled_provider_never_counts_clean(self):
        x = base(); x["snapshots"][1]["status"] = "THROTTLED"
        p = compile_census(x, trusted_now=NOW)
        self.assertIn("PROVIDER_CENSUS_THROTTLED:gmail", p["reasons"])

    def test_unavailable_provider_holds(self):
        x = base(); x["snapshots"][1]["status"] = "UNAVAILABLE"
        self.assertIn("PROVIDER_CENSUS_UNAVAILABLE:gmail", compile_census(x, trusted_now=NOW)["reasons"])

    def test_ambiguous_provider_holds(self):
        x = base(); x["snapshots"][1]["status"] = "AMBIGUOUS"
        self.assertIn("PROVIDER_CENSUS_AMBIGUOUS:gmail", compile_census(x, trusted_now=NOW)["reasons"])

    def test_stale_snapshot_holds(self):
        x = base(); x["intent"]["requested_at"] = "2026-09-14T03:24:00Z"
        x["snapshots"][0]["observed_at"] = "2026-09-14T03:24:59Z"
        x["snapshots"][1]["observed_at"] = "2026-09-14T03:24:59Z"
        p = compile_census(x, trusted_now=NOW)
        self.assertIn("PROVIDER_CENSUS_STALE:gmail", p["reasons"])

    def test_exact_snapshot_age_boundary_is_valid(self):
        x = base(); x["intent"]["requested_at"] = "2026-09-14T03:25:00Z"
        x["snapshots"][0]["observed_at"] = "2026-09-14T03:25:00Z"
        x["snapshots"][1]["observed_at"] = "2026-09-14T03:25:00Z"
        self.assertEqual(compile_census(x, trusted_now=NOW)["decision"], "CLEAR_FOR_DOWNSTREAM_GATES")

    def test_future_snapshot_holds(self):
        x = base(); x["snapshots"][1]["observed_at"] = "2026-09-14T03:30:01Z"
        p = compile_census(x, trusted_now=NOW)
        self.assertIn("PROVIDER_CENSUS_FUTURE:gmail", p["reasons"])

    def test_missing_route_coverage_holds(self):
        x = base(); x["snapshots"][1]["covered_routes"] = []
        self.assertIn("PROVIDER_ROUTE_COVERAGE_MISSING:gmail", compile_census(x, trusted_now=NOW)["reasons"])

    def test_extra_route_coverage_holds(self):
        x = base(); x["snapshots"][1]["covered_routes"].append(H("f"))
        self.assertIn("PROVIDER_ROUTE_COVERAGE_UNKNOWN:gmail", compile_census(x, trusted_now=NOW)["reasons"])

    def test_unmapped_intent_route_holds(self):
        x = base(); x["intent"]["route_sha256"] = H("f")
        self.assertIn("INTENT_ROUTE_UNMAPPED", compile_census(x, trusted_now=NOW)["reasons"])

    def test_future_intent_holds(self):
        x = base(); x["intent"]["requested_at"] = "2026-09-14T03:30:01Z"
        self.assertIn("INTENT_REQUESTED_IN_FUTURE", compile_census(x, trusted_now=NOW)["reasons"])

    def test_event_after_snapshot_rejected(self):
        x = base(); x["snapshots"][1]["events"] = [event("PROVIDER_SENT", at="2026-09-14T03:29:57Z")]
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_event_on_unregistered_route_rejected(self):
        x = base(); x["snapshots"][1]["events"] = [event("PROVIDER_SENT", route=H("f"))]
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_duplicate_alias_rejected(self):
        x = base(); x["aliases"].append(copy.deepcopy(x["aliases"][0]))
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_duplicate_provider_snapshot_rejected(self):
        x = base(); x["snapshots"].append(copy.deepcopy(x["snapshots"][0]))
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_duplicate_evidence_event_rejected(self):
        x = base(); x["snapshots"][1]["events"] = [event("PROVIDER_SENT"), event("AUTO_REPLY")]
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_unknown_provider_rejected(self):
        x = base(); x["aliases"][0]["provider"] = "smtp"
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_unknown_event_rejected(self):
        x = base(); x["snapshots"][1]["events"] = [event("CLICKED")]
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_snapshot_before_current_intent_holds(self):
        x = base(); x["snapshots"][1]["observed_at"] = "2026-09-14T03:29:49Z"
        p = compile_census(x, trusted_now=NOW)
        self.assertIn("PROVIDER_CENSUS_BEFORE_INTENT:gmail", p["reasons"])

    def test_stale_intent_holds(self):
        x = base(); x["intent"]["requested_at"] = "2026-09-14T03:24:59Z"
        x["snapshots"][0]["observed_at"] = "2026-09-14T03:29:55Z"
        x["snapshots"][1]["observed_at"] = "2026-09-14T03:29:56Z"
        self.assertIn("INTENT_STALE", compile_census(x, trusted_now=NOW)["reasons"])

    def test_unregistered_snapshot_provider_rejected(self):
        x = base(); x["snapshots"].append({
            "provider": "slack", "status": "COMPLETE",
            "observed_at": "2026-09-14T03:29:57Z", "query_sha256": H("f"),
            "covered_routes": [], "events": []})
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_noncanonical_time_rejected(self):
        x = base(); x["intent"]["requested_at"] = "2026-09-14T03:29:50+00:00"
        with self.assertRaises(CensusError): compile_census(x, trusted_now=NOW)

    def test_custom_mapping_rejected(self):
        class D(dict): pass
        with self.assertRaises(CensusError): compile_census(D(base()), trusted_now=NOW)

    def test_order_independent(self):
        x = base(); y = base(); y["aliases"].reverse(); y["snapshots"].reverse()
        self.assertEqual(compile_census(x, trusted_now=NOW), compile_census(y, trusted_now=NOW))

    def test_packet_tamper_rejected(self):
        x = base(); p = compile_census(x, trusted_now=NOW); p["decision"] = "HOLD"
        with self.assertRaisesRegex(CensusError, "receipt"): verify_census(p, x, trusted_now=NOW)

    def test_input_drift_rejected(self):
        x = base(); p = compile_census(x, trusted_now=NOW); y = copy.deepcopy(x); y["intent"]["claim_scope"] = "claim-16864"
        with self.assertRaises(CensusError): verify_census(p, y, trusted_now=NOW)

    def test_time_drift_rejected(self):
        x = base(); p = compile_census(x, trusted_now=NOW)
        with self.assertRaises(CensusError): verify_census(p, x, trusted_now="2026-09-14T03:30:01Z")

    def test_no_pii_fields_in_packet(self):
        p = compile_census(base(), trusted_now=NOW); raw = json.dumps(p)
        self.assertNotIn("@", raw)
        self.assertNotIn("sophia", raw.lower())

    def test_downstream_lease_identity_is_canonical_existing_v1(self):
        p = compile_census(base(), trusted_now=NOW)
        import hashlib, json
        seam = {
            "schema": "outbound-connector-lease/v1",
            "buyer_scope": "elyanlabs.example",
            "opportunity": {
                "kind": "external",
                "authority": "github.com",
                "id": "scottcjn/rustchain-bounties/issues/16863",
            },
        }
        expected = hashlib.sha256(json.dumps(seam, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
        self.assertEqual(p["downstream_lease_seam_sha256"], expected)
        self.assertEqual(p["downstream_lease_branch"], "outbound-connector-lease/v1/" + expected)


    def test_clear_packet_expires_at_earliest_fixed_policy_boundary(self):
        p = compile_census(base(), trusted_now=NOW)
        # Intent is at 03:29:50, so fixed 300-second intent policy wins over
        # later provider snapshot expiries. Downstream users must not reuse the
        # packet after this exact instant.
        self.assertEqual(p["clear_until"], "2026-09-14T03:34:50Z")
        self.assertEqual([r["provider"] for r in p["provider_census"]], ["github", "gmail"])
        self.assertTrue(all(r["query_sha256"] for r in p["provider_census"]))

    def test_hold_packet_has_no_clear_expiry_and_preserves_known_event_from_throttled_provider(self):
        x = base()
        x["snapshots"][1]["status"] = "THROTTLED"
        x["snapshots"][1]["events"] = [event("PROVIDER_SENT")]
        p = compile_census(x, trusted_now=NOW)
        self.assertEqual(p["decision"], "HOLD")
        self.assertIsNone(p["clear_until"])
        self.assertIn("PROVIDER_CENSUS_THROTTLED:gmail", p["reasons"])
        self.assertIn("PRIOR_PROVIDER_TOUCH_PRESENT", p["reasons"])
        self.assertEqual(p["evidence"][0]["event"], "PROVIDER_SENT")
        gmail = next(r for r in p["provider_census"] if r["provider"] == "gmail")
        self.assertEqual(gmail["status"], "THROTTLED")
        self.assertEqual(gmail["history_events"], 1)

    def test_cli_roundtrip_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); src = td / "in.json"; out = td / "packet.json"
            src.write_text(json.dumps(base()), encoding="utf-8")
            env = dict(os.environ); env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
            cmd = [sys.executable, "-m", "revenue.cross_provider_outbound_census.census", "compile", "--input", str(src), "--trusted-now", NOW, "--out", str(out)]
            first = subprocess.run(cmd, env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(cmd, env=env, text=True, capture_output=True)
            self.assertEqual(second.returncode, 2)
            verify = subprocess.run([sys.executable, "-m", "revenue.cross_provider_outbound_census.census", "verify", "--input", str(src), "--trusted-now", NOW, "--packet", str(out)], env=env, text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)

    def test_cli_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); src = td / "in.json"; out = td / "packet.json"
            src.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            env = dict(os.environ); env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
            r = subprocess.run([sys.executable, "-m", "revenue.cross_provider_outbound_census.census", "compile", "--input", str(src), "--trusted-now", NOW, "--out", str(out)], env=env, text=True, capture_output=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("duplicate JSON key", r.stderr)


if __name__ == "__main__": unittest.main()
