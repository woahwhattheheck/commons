from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import revenue.cross_provider_outbound_census.census as c

H = lambda ch: ch * 64
NOW_DT = datetime(2026, 9, 14, 3, 30, 0, tzinfo=UTC)
NOW = "2026-09-14T03:30:00Z"


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(v):
    return hashlib.sha256(canon(v)).hexdigest()


def intent():
    return {
        "schema": c.INPUT_SCHEMA,
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
    }


def lease_seam_sha():
    raw = intent()["lease_input"]
    return hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()


def event(kind="PROVIDER_SENT", *, route=H("b"), at="2026-09-14T03:20:00Z", evidence=H("e")):
    return {
        "route_sha256": route,
        "event": kind,
        "event_at": at,
        "evidence_sha256": evidence,
    }


def seal(row):
    out = copy.deepcopy(row)
    out["receipt_sha256"] = digest(out)
    return out


def registry(*, aliases=None, generation=7, authority_id="host-retained-census-v1"):
    return seal(
        {
            "schema": c.REGISTRY_SCHEMA,
            "authority_id": authority_id,
            "seam_sha256": lease_seam_sha(),
            "generation": generation,
            "generated_at": "2026-09-14T03:29:40Z",
            "aliases": aliases
            or [
                {"provider": "github", "route_sha256": H("a")},
                {"provider": "gmail", "route_sha256": H("b")},
            ],
        }
    )


def provider(provider, *, generation=11, query_generation=19, status="COMPLETE", observed_at=None,
             covered_routes=None, events=None, registry_generation=7,
             registry_receipt_sha256=None, authority_id="host-retained-census-v1"):
    if observed_at is None:
        observed_at = "2026-09-14T03:29:55Z" if provider == "github" else "2026-09-14T03:29:56Z"
    if covered_routes is None:
        covered_routes = [H("a")] if provider == "github" else [H("b")]
    if registry_receipt_sha256 is None:
        registry_receipt_sha256 = registry(generation=registry_generation, authority_id=authority_id)["receipt_sha256"]
    return seal(
        {
            "schema": c.PROVIDER_SCHEMA,
            "authority_id": authority_id,
            "seam_sha256": lease_seam_sha(),
            "provider": provider,
            "registry_generation": registry_generation,
            "registry_receipt_sha256": registry_receipt_sha256,
            "generation": generation,
            "query_generation": query_generation,
            "status": status,
            "observed_at": observed_at,
            "query_sha256": H("c") if provider == "github" else H("d"),
            "covered_routes": covered_routes,
            "events": events or [],
        }
    )


class MemoryAuthority(c.RetainedAuthoritySource):
    def __init__(self, reg=None, receipts=None, authority_id="host-retained-census-v1"):
        self._authority_id = authority_id
        self.reg = copy.deepcopy(reg or registry(authority_id=authority_id))
        self.receipts = copy.deepcopy(receipts if receipts is not None else {
            "github": provider("github", authority_id=authority_id, registry_generation=self.reg["generation"], registry_receipt_sha256=self.reg["receipt_sha256"]),
            "gmail": provider("gmail", authority_id=authority_id, registry_generation=self.reg["generation"], registry_receipt_sha256=self.reg["receipt_sha256"]),
        })
        self.calls = []

    @property
    def authority_id(self):
        return self._authority_id


    def put(self, provider_name, **kwargs):
        self.receipts[provider_name] = provider(
            provider_name,
            authority_id=self._authority_id,
            registry_generation=self.reg["generation"],
            registry_receipt_sha256=self.reg["receipt_sha256"],
            **kwargs,
        )
        return self.receipts[provider_name]

    def load_alias_registry(self, seam_sha256):
        self.calls.append(("registry", seam_sha256))
        return copy.deepcopy(self.reg)

    def load_provider_census(self, seam_sha256, provider_name, registry_generation):
        self.calls.append(("provider", provider_name, registry_generation))
        row = self.receipts.get(provider_name)
        return None if row is None else copy.deepcopy(row)


def current(raw=None, authority=None, now=NOW_DT):
    with mock.patch.object(c, "_process_utc_now", return_value=now):
        return c.compile_current(intent() if raw is None else raw, MemoryAuthority() if authority is None else authority)


class TestAuthorityBoundary(unittest.TestCase):
    def test_clean_current_uses_retained_registry_and_receipts(self):
        auth = MemoryAuthority()
        packet = current(authority=auth)
        self.assertEqual(packet["decision"], "CLEAR_FOR_DOWNSTREAM_GATES")
        self.assertEqual(packet["summary"]["required_providers"], ["github", "gmail"])
        self.assertEqual([x[0] for x in auth.calls].count("provider"), 2)
        self.assertFalse(packet["authority"]["external_send_authorized"])

    def test_candidate_cannot_supply_aliases(self):
        raw = intent(); raw["aliases"] = [{"provider": "github", "route_sha256": H("a")}]
        with self.assertRaisesRegex(c.CensusError, "input fields differ"):
            current(raw)

    def test_candidate_cannot_supply_provider_snapshots(self):
        raw = intent(); raw["snapshots"] = []
        with self.assertRaisesRegex(c.CensusError, "input fields differ"):
            current(raw)

    def test_omitting_gmail_from_candidate_is_impossible_and_retained_gmail_sent_blocks(self):
        auth = MemoryAuthority()
        auth.put("gmail", events=[event("PROVIDER_SENT")])
        packet = current(authority=auth)
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("PRIOR_PROVIDER_TOUCH_PRESENT", packet["reasons"])
        self.assertEqual(packet["summary"]["required_providers"], ["github", "gmail"])

    def test_claimant_forged_complete_empty_snapshot_field_is_rejected(self):
        raw = intent()
        raw["snapshots"] = [provider("gmail", events=[])]
        auth = MemoryAuthority()
        auth.put("gmail", events=[event("PROVIDER_SENT")])
        with self.assertRaises(c.CensusError):
            current(raw, auth)

    def test_plain_dict_is_not_authority_capability(self):
        with self.assertRaisesRegex(c.CensusError, "RetainedAuthoritySource"):
            current(authority={})

    def test_operational_api_has_no_trusted_now_argument(self):
        with self.assertRaises(TypeError):
            c.compile_current(intent(), MemoryAuthority(), trusted_now="2025-01-01T00:00:00Z")

    def test_historical_audit_never_emits_operational_clear(self):
        packet = c.audit_census(intent(), MemoryAuthority(), historical_as_of=NOW)
        self.assertEqual(packet["decision"], "AUDIT_ONLY_CLEAR")
        self.assertIsNone(packet["clear_until"])
        self.assertTrue(packet["authority"]["historical_audit_only"])

    def test_verify_rejects_audit_packet(self):
        packet = c.audit_census(intent(), MemoryAuthority(), historical_as_of=NOW)
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT):
            with self.assertRaisesRegex(c.CensusError, "only current packet"):
                c.verify_current(packet, intent(), MemoryAuthority())

    def test_registry_receipt_tamper_rejected(self):
        reg = registry(); reg["aliases"] = reg["aliases"][:1]
        with self.assertRaisesRegex(c.CensusError, "alias_registry receipt mismatch"):
            current(authority=MemoryAuthority(reg=reg))

    def test_provider_receipt_tamper_rejected(self):
        auth = MemoryAuthority(); auth.receipts["gmail"]["events"] = []
        auth.receipts["gmail"]["query_sha256"] = H("f")
        with self.assertRaisesRegex(c.CensusError, "provider_census.gmail receipt mismatch"):
            current(authority=auth)

    def test_authority_id_mismatch_rejected(self):
        reg = registry(authority_id="different-authority")
        with self.assertRaisesRegex(c.CensusError, "authority_id mismatch"):
            current(authority=MemoryAuthority(reg=reg))

    def test_provider_wrong_registry_generation_rejected(self):
        auth = MemoryAuthority(); auth.receipts["gmail"] = provider("gmail", registry_generation=6, registry_receipt_sha256=auth.reg["receipt_sha256"])
        with self.assertRaisesRegex(c.CensusError, "registry generation mismatch"):
            current(authority=auth)

    def test_provider_receipt_cannot_transplant_across_same_generation_different_registry(self):
        auth = MemoryAuthority()
        old = auth.receipts["gmail"]
        new_reg = registry(aliases=[
            {"provider": "github", "route_sha256": H("a")},
            {"provider": "gmail", "route_sha256": H("b")},
            {"provider": "slack", "route_sha256": H("f")},
        ], generation=7)
        auth.reg = new_reg
        auth.receipts["gmail"] = old
        auth.put("github")
        auth.put("slack", covered_routes=[H("f")])
        with self.assertRaisesRegex(c.CensusError, "registry receipt mismatch"):
            current(authority=auth)

    def test_provider_wrong_seam_rejected(self):
        auth = MemoryAuthority(); row = provider("gmail"); row["seam_sha256"] = H("f"); row = seal({k:v for k,v in row.items() if k!="receipt_sha256"}); auth.receipts["gmail"] = row
        with self.assertRaisesRegex(c.CensusError, "seam mismatch"):
            current(authority=auth)

    def test_retained_registry_unmapped_intent_holds(self):
        reg = registry(aliases=[{"provider":"gmail","route_sha256":H("b")}])
        auth = MemoryAuthority(reg=reg); auth.receipts = {"gmail": provider("gmail", registry_generation=reg["generation"], registry_receipt_sha256=reg["receipt_sha256"])}
        packet = current(authority=auth)
        self.assertIn("INTENT_ROUTE_UNMAPPED_BY_RETAINED_REGISTRY", packet["reasons"])

    def test_missing_retained_provider_census_holds(self):
        auth = MemoryAuthority(); del auth.receipts["gmail"]
        packet = current(authority=auth)
        self.assertIn("PROVIDER_CENSUS_MISSING:gmail", packet["reasons"])

    def test_throttled_retained_provider_holds(self):
        auth = MemoryAuthority(); auth.put("gmail", status="THROTTLED")
        self.assertIn("PROVIDER_CENSUS_THROTTLED:gmail", current(authority=auth)["reasons"])

    def test_unavailable_retained_provider_holds(self):
        auth = MemoryAuthority(); auth.put("gmail", status="UNAVAILABLE")
        self.assertIn("PROVIDER_CENSUS_UNAVAILABLE:gmail", current(authority=auth)["reasons"])

    def test_ambiguous_retained_provider_holds(self):
        auth = MemoryAuthority(); auth.put("gmail", status="AMBIGUOUS")
        self.assertIn("PROVIDER_CENSUS_AMBIGUOUS:gmail", current(authority=auth)["reasons"])

    def test_retained_provider_missing_route_coverage_holds(self):
        auth = MemoryAuthority(); auth.put("gmail", covered_routes=[])
        self.assertIn("PROVIDER_ROUTE_COVERAGE_MISSING:gmail", current(authority=auth)["reasons"])

    def test_provider_event_on_unregistered_route_rejected(self):
        auth = MemoryAuthority(); auth.put("gmail", events=[event(route=H("f"))])
        with self.assertRaisesRegex(c.CensusError, "not in retained registry"):
            current(authority=auth)

    def test_retained_snapshot_before_intent_holds(self):
        auth = MemoryAuthority(); auth.put("gmail", observed_at="2026-09-14T03:29:49Z")
        self.assertIn("PROVIDER_CENSUS_BEFORE_INTENT:gmail", current(authority=auth)["reasons"])

    def test_retained_snapshot_stale_holds(self):
        raw = intent(); raw["intent"]["requested_at"] = "2026-09-14T03:25:00Z"
        reg = registry(); unsigned = {k:v for k,v in reg.items() if k != "receipt_sha256"}; unsigned["generated_at"] = "2026-09-14T03:24:59Z"; reg = seal(unsigned)
        auth = MemoryAuthority(reg=reg); auth.put("gmail", observed_at="2026-09-14T03:25:00Z"); auth.put("github", observed_at="2026-09-14T03:25:00Z")
        # exactly 300 seconds is permitted
        self.assertEqual(current(raw, auth)["decision"], "CLEAR_FOR_DOWNSTREAM_GATES")
        later = NOW_DT + timedelta(seconds=1)
        self.assertIn("PROVIDER_CENSUS_STALE:gmail", current(raw, auth, later)["reasons"])


    def test_future_retained_registry_holds(self):
        reg = registry(); unsigned = {k:v for k,v in reg.items() if k != "receipt_sha256"}; unsigned["generated_at"] = "2026-09-14T03:30:01Z"; reg = seal(unsigned)
        packet = current(authority=MemoryAuthority(reg=reg))
        self.assertIn("ALIAS_REGISTRY_GENERATED_IN_FUTURE", packet["reasons"])

    def test_provider_census_before_retained_registry_generation_holds(self):
        reg = registry(); unsigned = {k:v for k,v in reg.items() if k != "receipt_sha256"}; unsigned["generated_at"] = "2026-09-14T03:29:55Z"; reg = seal(unsigned)
        auth = MemoryAuthority(reg=reg); auth.put("github", observed_at="2026-09-14T03:29:54Z")
        packet = current(authority=auth)
        self.assertIn("PROVIDER_CENSUS_BEFORE_REGISTRY:github", packet["reasons"])

    def test_future_provider_census_holds(self):
        auth = MemoryAuthority(); auth.put("gmail", observed_at="2026-09-14T03:30:01Z")
        self.assertIn("PROVIDER_CENSUS_FUTURE:gmail", current(authority=auth)["reasons"])

    def test_stale_intent_holds(self):
        raw = intent(); raw["intent"]["requested_at"] = "2026-09-14T03:24:59Z"
        self.assertIn("INTENT_STALE", current(raw)["reasons"])

    def test_future_intent_holds(self):
        raw = intent(); raw["intent"]["requested_at"] = "2026-09-14T03:30:01Z"
        self.assertIn("INTENT_REQUESTED_IN_FUTURE", current(raw)["reasons"])


class TestHistoricalEvidence(unittest.TestCase):
    def _assert_reason(self, kind, reason):
        auth = MemoryAuthority(); auth.put("gmail", events=[event(kind)])
        self.assertIn(reason, current(authority=auth)["reasons"])

    def test_provider_sent(self): self._assert_reason("PROVIDER_SENT", "PRIOR_PROVIDER_TOUCH_PRESENT")
    def test_human_reply(self): self._assert_reason("HUMAN_REPLY", "PRIOR_PROVIDER_TOUCH_PRESENT")
    def test_auto_reply(self): self._assert_reason("AUTO_REPLY", "PRIOR_PROVIDER_TOUCH_PRESENT")
    def test_unsubscribe(self): self._assert_reason("UNSUBSCRIBE", "SUPPRESSION_HISTORY_PRESENT")
    def test_dnr(self): self._assert_reason("DNR", "SUPPRESSION_HISTORY_PRESENT")
    def test_hard_bounce(self): self._assert_reason("HARD_BOUNCE", "ROUTE_REPAIR_REQUIRED")
    def test_soft_bounce(self): self._assert_reason("SOFT_BOUNCE", "ROUTE_REPAIR_REQUIRED")
    def test_provider_rejected(self): self._assert_reason("PROVIDER_REJECTED", "ROUTE_REPAIR_REQUIRED")
    def test_ambiguous_effect(self): self._assert_reason("AMBIGUOUS_EFFECT", "AMBIGUOUS_PROVIDER_EFFECT_PRESENT")

    def test_known_event_survives_throttled_state(self):
        auth = MemoryAuthority(); auth.put("gmail", status="THROTTLED", events=[event("PROVIDER_SENT")])
        packet = current(authority=auth)
        self.assertIn("PROVIDER_CENSUS_THROTTLED:gmail", packet["reasons"])
        self.assertIn("PRIOR_PROVIDER_TOUCH_PRESENT", packet["reasons"])
        self.assertEqual(packet["evidence"][0]["provider"], "gmail")


class TestVerification(unittest.TestCase):
    def test_current_packet_verifies_with_same_retained_generation(self):
        auth = MemoryAuthority()
        packet = current(authority=auth)
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT + timedelta(seconds=5)):
            result = c.verify_current(packet, intent(), auth)
        self.assertTrue(result["ok"])

    def test_packet_tamper_rejected(self):
        auth = MemoryAuthority(); packet = current(authority=auth); packet["decision"] = "HOLD"
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT):
            with self.assertRaisesRegex(c.CensusError, "receipt mismatch"):
                c.verify_current(packet, intent(), auth)

    def test_packet_older_than_30_seconds_rejected_even_if_historical_inputs_were_clean(self):
        auth = MemoryAuthority(); packet = current(authority=auth)
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT + timedelta(seconds=31)):
            with self.assertRaisesRegex(c.CensusError, "too old"):
                c.verify_current(packet, intent(), auth)

    def test_future_packet_time_rejected(self):
        auth = MemoryAuthority(); packet = current(authority=auth)
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT - timedelta(seconds=1)):
            with self.assertRaisesRegex(c.CensusError, "future"):
                c.verify_current(packet, intent(), auth)

    def test_authority_generation_change_invalidates_packet(self):
        auth = MemoryAuthority(); packet = current(authority=auth)
        auth.reg = registry(generation=8)
        auth.put("github")
        auth.put("gmail")
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT):
            with self.assertRaises(c.CensusError):
                c.verify_current(packet, intent(), auth)

    def test_provider_generation_change_invalidates_packet(self):
        auth = MemoryAuthority(); packet = current(authority=auth)
        auth.put("gmail", generation=12)
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT):
            with self.assertRaisesRegex(c.CensusError, r"exact input \+ retained authority generation"):
                c.verify_current(packet, intent(), auth)

    def test_input_drift_invalidates_packet(self):
        auth = MemoryAuthority(); packet = current(authority=auth); changed = intent(); changed["intent"]["claim_scope"] = "claim-16864"
        with mock.patch.object(c, "_process_utc_now", return_value=NOW_DT):
            with self.assertRaises(c.CensusError):
                c.verify_current(packet, changed, auth)

    def test_clear_until_is_earliest_policy_boundary(self):
        packet = current()
        self.assertEqual(packet["clear_until"], "2026-09-14T03:34:50Z")

    def test_no_raw_route_or_message_pii_is_emitted(self):
        raw = json.dumps(current())
        self.assertNotIn("@", raw)
        self.assertNotIn("recipient", raw.lower())
        self.assertNotIn("subject", raw.lower())

    def test_write_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "packet.json"
            c.write_exclusive(p, {"a": 1})
            with self.assertRaises(c.CensusError): c.write_exclusive(p, {"b": 2})


if __name__ == "__main__":
    unittest.main()
