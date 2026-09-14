from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.outbound_send_guard import relationship_census as rc

KEY = bytes.fromhex("42" * 32)
ATTACKER_KEY = bytes.fromhex("99" * 32)
NOW = datetime(2026, 9, 14, 2, 40, tzinfo=timezone.utc)
R1, R2, EVENT, WORKSPACE = "11" * 32, "22" * 32, "33" * 32, "44" * 32
REL, TARGET = "worker-alpha", "account-funto-v1"


def sign(raw, key=KEY):
    candidate = copy.deepcopy(raw)
    candidate["authority"]["signature_sha256"] = "00" * 32
    normalized = rc._normalize(candidate)
    raw["authority"]["signature_sha256"] = rc.compute_signature(normalized, key)
    return raw


def manifest(state="ACTIVE_OWNER", owner=REL, generation=3, key=KEY):
    rows = [
        {
            "route_sha256": route,
            "target_binding_sha256": rc.target_binding_sha256(TARGET, route),
            "state": state,
            "owner": owner,
            "generation": generation,
            "observed_at": "2026-09-14T02:38:00Z",
            "event_sha256": EVENT,
        }
        for route in (R1, R2)
    ]
    raw = {
        "schema_version": rc.CENSUS_SCHEMA,
        "target_scope": TARGET,
        "route_sha256s": [R2, R1],
        "current_worker": REL,
        "claimed_generation": generation,
        "census": {
            "provider": "gmail",
            "workspace_sha256": WORKSPACE,
            "snapshot_id": "snap-001",
            "snapshot_at": "2026-09-14T02:39:00Z",
            "coverage_started_at": "2025-09-14T00:00:00Z",
            "complete": True,
            "route_observations": rows,
            "relationship": {"state": state, "owner": owner, "generation": generation},
            "transfer": None,
        },
        "authority": {
            "schema_version": rc.AUTHORITY_SCHEMA,
            "scheme": "HMAC-SHA256",
            "key_id": "gmail-workspace-key-v1",
            "signature_sha256": "00" * 32,
        },
    }
    return sign(raw, key)


def replay(raw, key=KEY, now=NOW):
    return rc._evaluate_at(raw, provider_hmac_key=key, now=now)


class RelationshipCensusV2Tests(unittest.TestCase):
    def test_owner_and_clear_are_projection_only(self):
        owner = replay(manifest())["payload"]
        self.assertEqual((owner["decision"], owner["projected_custody"]), ("HOLD", "CURRENT_OWNER"))
        self.assertTrue(owner["integrity_hmac_valid"])
        self.assertFalse(owner["provider_origin_attested"])
        self.assertFalse(owner["current_authority"])
        self.assertFalse(owner["external_send_authorized"])
        self.assertIn("PROVIDER_ORIGIN_UNATTESTED", owner["reasons"])
        clear = replay(manifest("CLEAR", None, 0))["payload"]
        self.assertEqual((clear["decision"], clear["projected_custody"]), ("HOLD", "CUSTODY_CLEAR"))

    def test_self_minted_valid_hmac_never_becomes_authority(self):
        payload = replay(manifest(key=ATTACKER_KEY), key=ATTACKER_KEY)["payload"]
        self.assertTrue(payload["integrity_hmac_valid"])
        self.assertEqual(payload["authority_scope"], "SUPPLIED_SECRET_INTEGRITY_ONLY")
        self.assertEqual(payload["decision"], "HOLD")
        self.assertIn("PROVIDER_ORIGIN_UNATTESTED", payload["reasons"])

    def test_public_api_removed_caller_clock_policy_and_exact_digest(self):
        raw = manifest()
        for kwargs in (
            {"now": NOW},
            {"max_snapshot_age_seconds": 604800},
            {"max_future_skew_seconds": 86400},
            {"source_sha256": "00" * 32},
        ):
            with self.assertRaises(TypeError):
                rc.evaluate(raw, provider_hmac_key=KEY, **kwargs)
        with self.assertRaises(TypeError):
            rc.evaluate_bytes(json.dumps(raw).encode(), provider_hmac_key=KEY, now=NOW)

    def test_historical_replay_is_never_current(self):
        payload = replay(manifest(), now=NOW - timedelta(seconds=30))["payload"]
        self.assertFalse(payload["current_authority"])
        self.assertEqual(payload["currentness_policy"]["policy_id"], rc.LIVE_POLICY_ID)
        self.assertEqual(payload["currentness_policy"]["max_snapshot_age_seconds"], 900)
        self.assertEqual(payload["currentness_policy"]["max_future_skew_seconds"], 300)
        self.assertIn("HISTORICAL_REPLAY_NOT_LIVE_AUTHORITY", payload["reasons"])

    def test_waiting_inbound_closed_and_contact_blocks_hold_at_both_levels(self):
        for state in (
            "WAITING_REPLY", "INBOUND_NEEDS_OWNER", "UNSUBSCRIBED", "DNR",
            "HARD_BOUNCE", "TRANSFER_PENDING", "CLOSED",
        ):
            with self.subTest(state=state):
                payload = replay(manifest(state, REL))["payload"]
                self.assertEqual(payload["projected_custody"], "UNPROVEN")
                self.assertIn(f"RELATIONSHIP_STATE_BLOCKED:{state}", payload["reasons"])
                self.assertTrue(any(x.startswith("ROUTE_STATE_BLOCKED:") and x.endswith(f":{state}") for x in payload["reasons"]))

    def test_stale_future_incomplete_and_signature_fail_closed(self):
        stale = manifest(); stale["census"]["snapshot_at"] = "2026-09-14T01:00:00Z"; stale = sign(stale)
        future = manifest(); future["census"]["snapshot_at"] = "2026-09-14T03:00:00Z"; future = sign(future)
        incomplete = manifest(); incomplete["census"]["complete"] = False; incomplete = sign(incomplete)
        badsig = manifest(); badsig["authority"]["signature_sha256"] = "ff" * 32
        self.assertIn("SNAPSHOT_STALE", replay(stale)["payload"]["reasons"])
        self.assertIn("SNAPSHOT_IN_FUTURE", replay(future)["payload"]["reasons"])
        self.assertIn("CENSUS_INCOMPLETE", replay(incomplete)["payload"]["reasons"])
        self.assertFalse(replay(badsig)["payload"]["integrity_hmac_valid"])

    def test_cross_target_transplant_still_holds(self):
        raw = manifest(); raw["target_scope"] = "account-other-v1"; raw = sign(raw)
        self.assertTrue(any(x.startswith("TARGET_BINDING_MISMATCH:") for x in replay(raw)["payload"]["reasons"]))

    def test_valid_transfer_is_projection_only(self):
        raw = manifest("TRANSFERRED", "worker-new", 4)
        raw["current_worker"], raw["claimed_generation"] = "worker-new", 4
        raw["census"]["transfer"] = {
            "schema_version": rc.TRANSFER_SCHEMA,
            "target_route_set_sha256": rc.route_set_sha256(TARGET, [R1, R2]),
            "from_owner": REL, "to_owner": "worker-new", "from_generation": 3, "to_generation": 4,
            "release_actor": REL, "release_authority": "OWNER", "released_at": "2026-09-14T02:36:00Z",
            "release_ref_sha256": "55" * 32, "accept_actor": "worker-new",
            "accepted_at": "2026-09-14T02:37:00Z", "accept_ref_sha256": "66" * 32,
        }
        payload = replay(sign(raw))["payload"]
        self.assertEqual(payload["projected_custody"], "CURRENT_OWNER")
        self.assertEqual(payload["decision"], "HOLD")
        self.assertRegex(payload["transfer_receipt_sha256"], r"^[0-9a-f]{64}$")

    def test_strict_json_pii_and_exact_bytes_are_preserved(self):
        with self.assertRaises(rc.CensusError): rc.parse_json_bytes(b'{"x":1,"x":2}')
        with self.assertRaises(rc.CensusError): rc.parse_json_bytes(b'{"x":NaN}')
        raw = manifest(); raw["current_worker"] = "worker@example.com"
        with self.assertRaises(rc.CensusError): replay(raw)
        encoded = json.dumps(manifest(), sort_keys=True).encode()
        payload = rc.evaluate_bytes(encoded, provider_hmac_key=KEY)["payload"]
        self.assertEqual(payload["source_exact_bytes_sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertEqual(payload["decision"], "HOLD")

    def test_cli_removed_wideners_and_valid_input_publishes_hold(self):
        for flag, value in (("--max-snapshot-age-seconds", "604800"), ("--max-future-skew-seconds", "86400")):
            with self.assertRaises(SystemExit) as ctx:
                rc.main(["--census", "x", "--out", "y", flag, value])
            self.assertEqual(ctx.exception.code, 2)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); census, out = td / "census.json", td / "receipt.json"
            census.write_text(json.dumps(manifest()), encoding="utf-8")
            prior = os.environ.get("OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX")
            os.environ["OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX"] = KEY.hex()
            try: code = rc.main(["--census", str(census), "--out", str(out)])
            finally:
                if prior is None: os.environ.pop("OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX", None)
                else: os.environ["OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX"] = prior
            self.assertEqual(code, 4)
            self.assertEqual(json.loads(out.read_text())["payload"]["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
