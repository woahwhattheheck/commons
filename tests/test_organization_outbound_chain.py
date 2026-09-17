from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from revenue.organization_outbound_chain import chain
from revenue.organization_outbound_chain.registry import find_bypasses, registered_provider_names


ORG = "1" * 64
CAP = bytes.fromhex("ab" * 32)
PRESSURE = "2" * 64
AUTH = "3" * 64
LEDGER = "4" * 64
LOWER_ANCHOR = "5" * 40
ACTIVE_GENERATION = "6" * 40


class FakeStore:
    def __init__(self, raw: bytes, generation: str = ACTIVE_GENERATION):
        self.raw = raw
        self.generation = generation

    def get_active(self, org_fingerprint: str):
        if org_fingerprint != ORG:
            return None
        return self.raw, self.generation


def valid_lease(*, prospect: bytes = b"person-a", route: bytes = b"person-a@example.test", key: str = "opportunity-key"):
    body = {
        "schema": "commons.organization-outbound-lease/v2",
        "leaseId": "7" * 64,
        "intentSha256": "8" * 64,
        "leaseNonce": "9" * 64,
        "claimId": "claim-a",
        "organizationFingerprint": ORG,
        "prospectFingerprint": chain.prospect_fingerprint(ORG, prospect),
        "routeCommitment": chain.route_commitment(ORG, route),
        "opportunityCommitment": chain.opportunity_commitment(ORG, "buyer.example", key),
        "holderCapabilityCommitment": chain.holder_capability_commitment(CAP),
        "requestedAt": "2026-09-17T19:00:00Z",
        "pressureReceiptSha256": PRESSURE,
        "authorityCommitment": AUTH,
        "ledgerCommitment": LEDGER,
        "pressureVerifiedAt": "2026-09-17T18:59:59Z",
        "externalSendAuthorized": False,
    }
    body["leaseSha256"] = hashlib.sha256(chain.lease_canonical_json(body)).hexdigest()
    return body


class ChainHelpersTest(unittest.TestCase):
    def test_active_lease_requires_exact_bytes_generation_and_private_capability(self):
        lease = valid_lease()
        raw = chain.lease_canonical_json(lease)
        store = FakeStore(raw)
        parsed, observed = chain._active_organization_lease(
            store=store,
            lease_receipt=lease,
            active_generation=ACTIVE_GENERATION,
            holder_capability=CAP,
        )
        self.assertEqual(parsed["leaseId"], lease["leaseId"])
        self.assertEqual(observed, raw)
        with self.assertRaises(chain.ChainError):
            chain._active_organization_lease(
                store=store,
                lease_receipt=lease,
                active_generation="a" * 40,
                holder_capability=CAP,
            )
        with self.assertRaises(chain.ChainError):
            chain._active_organization_lease(
                store=store,
                lease_receipt=lease,
                active_generation=ACTIVE_GENERATION,
                holder_capability=bytes.fromhex("cd" * 32),
            )

    def test_pressure_must_be_current_and_exact_generation_bound(self):
        lease = valid_lease()
        current = {
            "decision": chain.READY,
            "external_send_authorized": False,
            "receipt_sha256": PRESSURE,
            "authority_sha256": AUTH,
            "ledger_sha256": LEDGER,
        }
        with patch.object(chain, "verify_receipt_current", return_value=current):
            self.assertEqual(chain._pressure_current(b"signed-pressure", lease)["receipt_sha256"], PRESSURE)
        for field in ("receipt_sha256", "authority_sha256", "ledger_sha256"):
            bad = dict(current)
            bad[field] = "f" * 64
            with patch.object(chain, "verify_receipt_current", return_value=bad):
                with self.assertRaises(chain.ChainError):
                    chain._pressure_current(b"signed-pressure", lease)

    def test_same_canonical_org_and_opportunity_define_same_initial_event_seam(self):
        opp = chain.opportunity_commitment(ORG, "buyer.example", "opportunity-key")
        self.assertEqual(chain._event_key(ORG, opp), chain._event_key(ORG, opp))
        self.assertNotIn("person-a", chain._event_key(ORG, opp))
        self.assertNotIn("price", chain._event_key(ORG, opp))


class ChainCompositionTest(unittest.TestCase):
    def _run(self, *, prospect=b"person-a", route=b"person-a@example.test", provider_callback=None, consumer_receipt=None):
        lease = valid_lease()
        identity = SimpleNamespace(repo="woahwhattheheck/commons", buyer_scope="buyer.example")
        pressure = {
            "decision": chain.READY,
            "external_send_authorized": False,
            "receipt_sha256": PRESSURE,
            "authority_sha256": AUTH,
            "ledger_sha256": LEDGER,
        }
        lower = {
            "anchor_sha": LOWER_ANCHOR,
            "slot_ref": "refs/tags/slot",
            "slot_tag_sha": "a" * 40,
            "slot_metadata_sha256": "b" * 64,
            "lower_lease_ref": "refs/tags/lower",
            "lower_lease_tag_object_sha": "c" * 40,
            "lower_lease_claim_capability_sha256": "d" * 64,
            "lower_lease_preflight_sha256": "e" * 64,
            "lower_lease_claim_id": "claim-lower",
            "custody_generation": 1,
            "custody_history_sha256": "f" * 64,
            "custody_check_sha256": "0" * 64,
            "custody_basis": "WHOLE",
        }
        calls = []
        if provider_callback is None:
            provider_callback = lambda key, raw: calls.append((key, raw))
        if consumer_receipt is None:
            consumer_receipt = {
                "receipt_sha256": "a" * 64,
                "decision": "SENT",
                "terminal_state": "SENT",
                "external_send_completed": True,
                "prior_send_observed": False,
            }

        def fake_initial(*args, send_once, **kwargs):
            send_once()
            return {"receipt_sha256": "b" * 64, "provider_callback_invoked": True}

        def fake_consume(intent, *, host_raw, transport, authority_probe, provider_callback):
            self.assertEqual(host_raw["buyer_scope"], ORG)
            self.assertEqual(intent["event_key"], host_raw["event_key"])
            self.assertIsNotNone(authority_probe())
            provider_callback("tjlabs-outbound-v1:test")
            return dict(consumer_receipt)

        with (
            patch.object(chain, "_active_organization_lease", return_value=(lease, b"lease")),
            patch.object(chain, "_pressure_current", return_value=pressure),
            patch.object(chain, "_identity_and_key", return_value=(identity, "opportunity-key")),
            patch.object(chain, "_lower_authority_current", return_value=lower),
            patch.object(chain.initial_slot, "execute_initial_outreach", side_effect=fake_initial),
            patch.object(chain, "consume_once", side_effect=fake_consume),
            patch.object(chain, "_finalize_organization_lease", return_value={"outcome_sha256": "c" * 64}),
        ):
            result = chain.execute_guarded_initial_outreach(
                {"schema": "ignored-by-mock"},
                actor_owner="Sol-Z",
                actor_operation="issue-14269",
                lower_lease_receipt={"anchor_sha": LOWER_ANCHOR},
                lower_claim_capability="private-lower",
                git_transport=lambda *args: (404, None),
                pressure_receipt_data=b"pressure",
                organization_lease_store=object(),
                organization_lease_receipt=lease,
                organization_lease_generation=ACTIVE_GENERATION,
                organization_holder_capability=CAP,
                prospect_identity=prospect,
                route_identity=route,
                provider="gmail",
                provider_request_bytes=b"provider-request",
                provider_callback=provider_callback,
            )
        return result, calls

    def test_exact_winner_can_reach_provider_once_and_receipt_never_mints_authority(self):
        result, calls = self._run()
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["decision"], "SENT")
        self.assertTrue(result["external_send_completed"])
        self.assertFalse(result["external_send_authorized"])
        self.assertFalse(result["replay_or_retry_authorized"])
        self.assertFalse(result["payment_or_revenue_inferred"])
        self.assertFalse(result["raw_capability_exported"])

    def test_same_org_different_prospect_cannot_reuse_winner_lease(self):
        result, calls = self._run()
        self.assertEqual(len(calls), 1)
        with self.assertRaises(chain.ChainError):
            self._run(prospect=b"person-b")

    def test_missing_action_specific_slot_is_zero_provider_calls(self):
        lease = valid_lease()
        identity = SimpleNamespace(repo="woahwhattheheck/commons", buyer_scope="buyer.example")
        calls = []
        with (
            patch.object(chain, "_active_organization_lease", return_value=(lease, b"lease")),
            patch.object(chain, "_pressure_current", return_value={"receipt_sha256": PRESSURE, "authority_sha256": AUTH, "ledger_sha256": LEDGER}),
            patch.object(chain, "_identity_and_key", return_value=(identity, "opportunity-key")),
            patch.object(chain.initial_slot, "execute_initial_outreach", return_value={"receipt_sha256": "b" * 64, "provider_callback_invoked": False}),
        ):
            result = chain.execute_guarded_initial_outreach(
                {}, actor_owner="Sol-Z", actor_operation="issue-14269",
                lower_lease_receipt={"anchor_sha": LOWER_ANCHOR}, lower_claim_capability="x",
                git_transport=lambda *args: (404, None), pressure_receipt_data=b"pressure",
                organization_lease_store=object(), organization_lease_receipt=lease,
                organization_lease_generation=ACTIVE_GENERATION, organization_holder_capability=CAP,
                prospect_identity=b"person-a", route_identity=b"person-a@example.test",
                provider="gmail", provider_request_bytes=b"req",
                provider_callback=lambda key, raw: calls.append((key, raw)),
            )
        self.assertEqual(calls, [])
        self.assertEqual(result["decision"], "HOLD_ACTION_SPECIFIC_AUTHORITY")
        self.assertFalse(result["external_send_completed"])

    def test_unknown_consumer_outcome_is_reconciliation_only(self):
        unknown = {
            "receipt_sha256": "a" * 64,
            "decision": "RECONCILE_REQUIRED",
            "terminal_state": "OUTCOME_UNKNOWN",
            "external_send_completed": False,
            "prior_send_observed": False,
        }
        result, calls = self._run(consumer_receipt=unknown)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["decision"], "RECONCILE_REQUIRED")
        self.assertEqual(result["terminal_state"], "OUTCOME_UNKNOWN")
        self.assertFalse(result["replay_or_retry_authorized"])


class RegistryTest(unittest.TestCase):
    def test_supported_provider_registry_is_explicit(self):
        self.assertEqual(registered_provider_names(), ("gmail", "slack_dm", "discord", "webhook_mail"))

    def test_direct_lower_primitive_or_provider_marker_fails_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "live.py").write_text(
                "def f():\n    execute_initial_outreach({})\n    slack_send_message('x')\n",
                encoding="utf-8",
            )
            violations = find_bypasses(root)
            self.assertIn("live.py:direct-initial-outreach", violations)
            self.assertTrue(any("provider-marker:slack_send_message(" in item for item in violations))

    def test_test_files_do_not_count_as_live_adapter_bypass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "test_fake.py").write_text("execute_initial_outreach({})\nslack_send_message('x')\n", encoding="utf-8")
            self.assertEqual(find_bypasses(root), [])

    def test_repository_has_no_unguarded_live_provider_path(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(find_bypasses(root), [])


if __name__ == "__main__":
    unittest.main()
