from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from revenue.organization_outbound_lease.core import (
    acquire_lease,
    canonical_json,
    finalize_lease,
    fingerprint_organization,
    mint_pressure_attestation_for_host,
    verify_lease_document,
)
from revenue.organization_outbound_lease.stores import FileLeaseStore, GitHubContentsLeaseStore, StoreConflict
from revenue.organization_outbound_lease.strict import parse_json_strict, write_exclusive

K1 = b"f" * 32
K2 = b"a" * 32
K3 = b"n" * 32
H = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64


def ts(offset_seconds=0):
    return (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def pressure(org, at=None, state="READY_FOR_SINGLE_WRITER_REVIEW"):
    body = {
        "schema": "commons.organization-pressure-attestation/v1",
        "organizationFingerprint": org,
        "pressureReceiptSha256": H,
        "authorityCommitment": H2,
        "ledgerCommitment": H3,
        "verifiedState": state,
        "verifiedAt": at or ts(-2),
    }
    return mint_pressure_attestation_for_host(body, K2)


def req(org, claim="claim-a", prospect=H4, route="5"*64, opp="6"*64, claimant="7"*64, requested_at=None, pressure_at=None):
    return {
        "schema": "commons.organization-outbound-acquire/v1",
        "claimId": claim,
        "organizationFingerprint": org,
        "prospectFingerprint": prospect,
        "routeCommitment": route,
        "opportunityCommitment": opp,
        "claimantCommitment": claimant,
        "requestedAt": requested_at or ts(-1),
        "pressureAttestation": pressure(org, at=pressure_at or ts(-2)),
    }


def fin(lease, outcome="UNSENT_RELEASED", oid="outcome-a", at=None):
    return {
        "schema": "commons.organization-outbound-finalize/v1",
        "organizationFingerprint": lease["organizationFingerprint"],
        "leaseId": lease["leaseId"],
        "leaseNonce": lease["leaseNonce"],
        "claimId": lease["claimId"],
        "outcomeId": oid,
        "outcome": outcome,
        "observedAt": at or ts(0),
        "evidenceCommitment": "8"*64,
    }


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.store = FileLeaseStore(self.td.name)
        self.org = fingerprint_organization(b"example-inc", K1)
        self.org2 = fingerprint_organization(b"other-inc", K1)

    def acquire(self, request=None, store=None):
        return acquire_lease(store or self.store, request or req(self.org), host_attestation_key=K2, lease_nonce_key=K3)

    def test_fingerprint_privacy_and_determinism(self):
        a = fingerprint_organization(b"Example Inc canonical", K1)
        self.assertEqual(a, fingerprint_organization(b"Example Inc canonical", K1))
        self.assertNotIn("Example", a)
        self.assertNotEqual(a, fingerprint_organization(b"Example Inc canonical", b"x"*32))

    def test_happy_acquire_and_exact_replay(self):
        r = req(self.org)
        one = self.acquire(r)
        two = self.acquire(r)
        self.assertEqual(one.state, "LEASE_ACQUIRED")
        self.assertFalse(one.replay)
        self.assertTrue(two.replay)
        self.assertEqual(one.lease["leaseSha256"], two.lease["leaseSha256"])
        self.assertFalse(one.lease["externalSendAuthorized"])

    def test_stale_exact_acquire_replay_recovers_without_new_authority(self):
        r = req(self.org)
        one = self.acquire(r)
        future = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=900)
        with patch("revenue.organization_outbound_lease.core._process_now", return_value=future):
            replay = self.acquire(r)
        self.assertTrue(replay.replay)
        self.assertEqual(replay.lease["leaseId"], one.lease["leaseId"])
        self.assertEqual(replay.active_generation, one.active_generation)

    def test_same_org_different_prospect_route_and_opportunity_collide(self):
        first = self.acquire()
        for variant in [
            req(self.org, claim="claim-b", prospect="9"*64),
            req(self.org, claim="claim-c", route="a"*64),
            req(self.org, claim="claim-d", opp="b"*64),
        ]:
            result = self.acquire(variant)
            self.assertEqual(result.state, "ORGANIZATION_ALREADY_LEASED")
            self.assertEqual(result.lease["leaseId"], first.lease["leaseId"])

    def test_different_organizations_independent(self):
        a = self.acquire(req(self.org, claim="a"))
        b = self.acquire(req(self.org2, claim="b"))
        self.assertEqual(a.state, "LEASE_ACQUIRED")
        self.assertEqual(b.state, "LEASE_ACQUIRED")
        self.assertNotEqual(a.lease["organizationFingerprint"], b.lease["organizationFingerprint"])

    def test_invalid_upstream_state_cannot_mint_attestation(self):
        with self.assertRaises(ValueError):
            pressure(self.org, state="HOLD")

    def test_bad_pressure_hmac_rejected(self):
        r = req(self.org)
        r["pressureAttestation"]["hmacSha256"] = "0"*64
        with self.assertRaises(ValueError):
            self.acquire(r)

    def test_cross_org_attestation_rejected(self):
        r = req(self.org)
        r["pressureAttestation"] = pressure(self.org2)
        with self.assertRaises(ValueError):
            self.acquire(r)

    def test_changed_upstream_generation_remains_blocked(self):
        first = self.acquire()
        r = req(self.org, claim="claim-new")
        body = deepcopy(r["pressureAttestation"]["body"])
        body["ledgerCommitment"] = "c"*64
        r["pressureAttestation"] = mint_pressure_attestation_for_host(body, K2)
        blocked = self.acquire(r)
        self.assertEqual(blocked.state, "ORGANIZATION_ALREADY_LEASED")
        self.assertEqual(blocked.lease["leaseId"], first.lease["leaseId"])

    def test_thread_race_exactly_one_distinct_claim_winner(self):
        barrier = threading.Barrier(8)
        results = []
        errors = []
        lock = threading.Lock()
        def worker(i):
            try:
                barrier.wait()
                out = self.acquire(req(self.org, claim=f"claim-{i}", prospect=f"{i+1:x}"*64))
                with lock:
                    results.append(out)
            except BaseException as exc:
                with lock:
                    errors.append(exc)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(errors, [], f"worker exceptions: {errors!r}")
        self.assertEqual(len(results), 8)
        wins = [r for r in results if r.state == "LEASE_ACQUIRED" and not r.replay]
        self.assertEqual(len(wins), 1)
        ids = {r.lease["leaseId"] for r in results}
        self.assertEqual(len(ids), 1)

    def test_finalize_unsent_persists_outcome_before_release_and_allows_reacquire(self):
        first = self.acquire()
        result = finalize_lease(self.store, fin(first.lease, "UNSENT_RELEASED"))
        self.assertTrue(result.active_released)
        self.assertIsNone(self.store.get_active(self.org))
        persisted = self.store.get_outcome(self.org, first.lease["leaseId"])
        self.assertIsNotNone(persisted)
        second = self.acquire(req(self.org, claim="claim-second", prospect="9"*64))
        self.assertEqual(second.state, "LEASE_ACQUIRED")
        self.assertNotEqual(first.lease["leaseId"], second.lease["leaseId"])

    def test_unsent_finalize_exact_replay_after_release_is_idempotent(self):
        first = self.acquire()
        request = fin(first.lease, "UNSENT_RELEASED", oid="release-replay")
        one = finalize_lease(self.store, request)
        self.assertFalse(one.replay)
        self.assertTrue(one.active_released)
        future = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=1200)
        with patch("revenue.organization_outbound_lease.core._process_now", return_value=future):
            two = finalize_lease(self.store, request)
        self.assertTrue(two.replay)
        self.assertTrue(two.active_released)
        self.assertEqual(two.outcome["outcomeSha256"], one.outcome["outcomeSha256"])
        self.assertIsNone(self.store.get_active(self.org))

    def test_old_unsent_finalize_replay_never_deletes_successor(self):
        first = self.acquire()
        request = fin(first.lease, "UNSENT_RELEASED", oid="release-before-successor")
        finalize_lease(self.store, request)
        successor = self.acquire(req(self.org, claim="successor", prospect="9"*64))
        replay = finalize_lease(self.store, request)
        self.assertTrue(replay.replay)
        current_raw, _ = self.store.get_active(self.org)
        current = json.loads(current_raw)
        self.assertEqual(current["leaseId"], successor.lease["leaseId"])

    def test_released_outcome_mutation_conflicts_on_replay(self):
        first = self.acquire()
        request = fin(first.lease, "UNSENT_RELEASED", oid="release-mutation")
        finalize_lease(self.store, request)
        changed = deepcopy(request)
        changed["evidenceCommitment"] = "d"*64
        with self.assertRaises(ValueError):
            finalize_lease(self.store, changed)

    def test_sent_and_unknown_do_not_release_or_reacquire(self):
        for outcome in ("SENT", "OUTCOME_UNKNOWN", "REJECTED", "HELD_AUTHORITY"):
            with self.subTest(outcome=outcome):
                root = tempfile.TemporaryDirectory(); self.addCleanup(root.cleanup)
                store = FileLeaseStore(root.name)
                first = self.acquire(store=store)
                result = finalize_lease(store, fin(first.lease, outcome, oid="o-"+outcome.lower()))
                self.assertFalse(result.active_released)
                blocked = self.acquire(req(self.org, claim="new-"+outcome.lower(), prospect="a"*64), store=store)
                self.assertEqual(blocked.state, "ORGANIZATION_ALREADY_LEASED")

    def test_cross_lease_finalization_rejected(self):
        first = self.acquire()
        f = fin(first.lease)
        f["leaseId"] = "0"*64
        with self.assertRaises(ValueError): finalize_lease(self.store, f)

    def test_outcome_before_acquire_rejected(self):
        first = self.acquire()
        with self.assertRaises(ValueError):
            finalize_lease(self.store, fin(first.lease, at=ts(-30)))

    def test_outcome_id_mutation_conflicts(self):
        first = self.acquire()
        f = fin(first.lease, outcome="SENT", oid="same")
        one = finalize_lease(self.store, f)
        self.assertFalse(one.replay)
        changed = deepcopy(f); changed["evidenceCommitment"] = "d"*64
        with self.assertRaises(ValueError): finalize_lease(self.store, changed)

    def test_stale_and_future_preflight_rejected(self):
        with self.assertRaises(ValueError):
            self.acquire(req(self.org, claim="stale", requested_at=ts(-301), pressure_at=ts(-302)))
        with self.assertRaises(ValueError):
            self.acquire(req(self.org, claim="future", requested_at=ts(10), pressure_at=ts(9)))

    def test_pressure_cannot_postdate_acquire(self):
        with self.assertRaises(ValueError):
            self.acquire(req(self.org, claim="reverse", requested_at=ts(-2), pressure_at=ts(-1)))

    def test_stale_outcome_rejected(self):
        first = self.acquire()
        with self.assertRaises(ValueError):
            finalize_lease(self.store, fin(first.lease, at=ts(-601)))

    def test_lease_digest_tamper_rejected(self):
        first = self.acquire()
        bad = deepcopy(first.lease); bad["routeCommitment"] = "e"*64
        with self.assertRaises(ValueError): verify_lease_document(bad)

    def test_duplicate_json_key_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError): parse_json_strict('{"a":1,"a":2}')
        with self.assertRaises(ValueError): parse_json_strict('{"a":NaN}')

    def test_bool_and_unknown_fields_rejected(self):
        r = req(self.org); r["unexpected"] = True
        with self.assertRaises(ValueError): self.acquire(r)

    def test_exclusive_output_refuses_overwrite_and_symlink(self):
        p = Path(self.td.name) / "receipt.json"
        write_exclusive(p, b"one")
        with self.assertRaises(FileExistsError): write_exclusive(p, b"two")
        target = Path(self.td.name) / "target"; target.write_text("x")
        link = Path(self.td.name) / "link"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(FileExistsError): write_exclusive(link, b"bad")


class FakeGitHubTests(unittest.TestCase):
    def test_create_conflict_and_conditional_delete_payload(self):
        calls = []
        def opener(req):
            body = req.data.decode() if req.data else None
            calls.append((req.method, req.full_url, body))
            if req.method == "PUT":
                return 201, b'{"content":{"sha":"blob123"}}'
            if req.method == "DELETE":
                return 200, b'{}'
            raise AssertionError(req.method)
        s = GitHubContentsLeaseStore(repository="o/r", branch="leases", token="t", opener=opener)
        sha = s.create_active("1"*64, b"{}")
        self.assertEqual(sha, "blob123")
        s.delete_active("1"*64, "blob123")
        delete_payload = json.loads(calls[-1][2])
        self.assertEqual(delete_payload["sha"], "blob123")
        self.assertEqual(delete_payload["branch"], "leases")

    def test_get_uses_ref_query_not_encoded_path(self):
        seen = []
        payload = {"type":"file","sha":"abc","content":"e30="}
        def opener(req):
            seen.append(req.full_url)
            return 200, json.dumps(payload).encode()
        s = GitHubContentsLeaseStore(repository="o/r", branch="lease/branch", token="t", opener=opener)
        self.assertEqual(s.get_active("1"*64), (b"{}", "abc"))
        self.assertIn("?ref=lease%2Fbranch", seen[0])
        self.assertNotIn("%3Fref", seen[0])

    def test_conflict_status_maps_to_store_conflict(self):
        def opener(req): return 422, b'{"message":"exists"}'
        s = GitHubContentsLeaseStore(repository="o/r", branch="leases", token="t", opener=opener)
        with self.assertRaises(StoreConflict): s.create_active("1"*64, b"{}")


if __name__ == "__main__":
    unittest.main()
