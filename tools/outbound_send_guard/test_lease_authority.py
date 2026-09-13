from __future__ import annotations

import copy
import hashlib
import json
import unittest

from tools.outbound_send_guard.atomic_lease import LeaseError, acquire, verify_receipt
from tools.outbound_send_guard.lease_authority import verify_authoritative_receipt

ANCHOR = "a" * 40
PREFLIGHT = "b" * 64
TAG = "c" * 40
OTHER = "d" * 40


def claim(**updates):
    value = {
        "repo": "woahwhattheheck/commons",
        "buyer_scope": "atlab.com",
        "offer_scope": "englewood-rfp-26-031-lims-teaming",
        "claimant": "Z-Meridian-913506-L91",
        "claim_id": "atl-englewood-zmer-20260913",
        "claim_started_at": "2026-09-13T09:26:20Z",
        "anchor_sha": ANCHOR,
        "preflight_sha256": PREFLIGHT,
    }
    value.update(updates)
    return value


def resign(receipt):
    material = dict(receipt)
    material.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = hashlib.sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()
    return receipt


class Store:
    def __init__(self):
        self.tag_payload = None
        self.tag_sha = TAG
        self.ref_sha = TAG
        self.ref_read_status = 200
        self.tag_read_status = 200
        self.calls = []
        self.tag_overrides = {}

    def __call__(self, method, path, body):
        self.calls.append((method, path, copy.deepcopy(body)))
        if method == "POST" and path.endswith("/git/tags"):
            self.tag_payload = copy.deepcopy(body)
            return 201, {"sha": self.tag_sha}
        if method == "POST" and path.endswith("/git/refs"):
            return 201, {"object": {"sha": self.ref_sha}}
        if method == "GET" and "/git/ref/" in path:
            if self.ref_read_status != 200:
                return self.ref_read_status, None
            return 200, {"object": {"sha": self.ref_sha}}
        if method == "GET" and "/git/tags/" in path:
            if self.tag_read_status != 200:
                return self.tag_read_status, None
            payload = {
                "sha": self.tag_sha,
                "tag": self.tag_payload["tag"],
                "message": self.tag_payload["message"],
                "object": copy.deepcopy(self.tag_payload["object"]),
                "tagger": copy.deepcopy(self.tag_payload["tagger"]),
            }
            payload.update(copy.deepcopy(self.tag_overrides))
            return 200, payload
        raise AssertionError((method, path))


def authoritative(store, receipt, **updates):
    kwargs = {
        "repo": "woahwhattheheck/commons",
        "buyer_scope": "atlab.com",
        "offer_scope": "englewood-rfp-26-031-lims-teaming",
        "preflight_sha256": PREFLIGHT,
        "transport": store,
    }
    kwargs.update(updates)
    return verify_authoritative_receipt(receipt, **kwargs)


class LeaseAuthorityTests(unittest.TestCase):
    def make(self):
        store = Store()
        receipt = acquire(claim(), store)
        store.calls.clear()
        return store, receipt

    def test_exact_live_ref_and_tag_metadata_pass(self):
        store, receipt = self.make()
        self.assertTrue(authoritative(store, receipt))
        self.assertEqual([call[0] for call in store.calls], ["GET", "GET"])

    def test_self_hash_forgery_passes_integrity_but_fails_authority(self):
        store, receipt = self.make()
        forged = copy.deepcopy(receipt)
        forged["claimant"] = "Forged-Seat"
        resign(forged)
        self.assertTrue(verify_receipt(forged))
        self.assertFalse(authoritative(store, forged))

    def test_forged_claim_id_against_real_tag_fails(self):
        store, receipt = self.make()
        forged = copy.deepcopy(receipt)
        forged["claim_id"] = "different-claim-id"
        resign(forged)
        self.assertTrue(verify_receipt(forged))
        self.assertFalse(authoritative(store, forged))

    def test_missing_ref_fails_closed_without_tag_read(self):
        store, receipt = self.make()
        store.ref_read_status = 404
        self.assertFalse(authoritative(store, receipt))
        self.assertEqual([call[0] for call in store.calls], ["GET"])

    def test_other_ref_object_fails_closed(self):
        store, receipt = self.make()
        store.ref_sha = OTHER
        self.assertFalse(authoritative(store, receipt))
        self.assertEqual([call[0] for call in store.calls], ["GET"])

    def test_tag_read_failure_fails_closed(self):
        store, receipt = self.make()
        store.tag_read_status = 503
        self.assertFalse(authoritative(store, receipt))

    def test_wrong_expected_preflight_fails_before_network(self):
        store, receipt = self.make()
        wrong = "e" * 64
        self.assertFalse(authoritative(store, receipt, preflight_sha256=wrong))
        self.assertEqual(store.calls, [])

    def test_wrong_expected_seam_fails_before_network(self):
        store, receipt = self.make()
        self.assertFalse(authoritative(store, receipt, offer_scope="different-offer"))
        self.assertEqual(store.calls, [])

    def test_forged_tag_metadata_claimant_fails(self):
        store, receipt = self.make()
        payload = json.loads(store.tag_payload["message"])
        payload["claimant"] = "Different-Seat"
        store.tag_overrides["message"] = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ) + "\n"
        self.assertFalse(authoritative(store, receipt))

    def test_forged_tag_metadata_preflight_fails(self):
        store, receipt = self.make()
        payload = json.loads(store.tag_payload["message"])
        payload["preflight_sha256"] = "e" * 64
        store.tag_overrides["message"] = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ) + "\n"
        self.assertFalse(authoritative(store, receipt))

    def test_wrong_tag_name_fails(self):
        store, receipt = self.make()
        store.tag_overrides["tag"] = "outbound-claim-v1-forged"
        self.assertFalse(authoritative(store, receipt))

    def test_wrong_tag_target_fails(self):
        store, receipt = self.make()
        store.tag_overrides["object"] = {"type": "commit", "sha": OTHER}
        self.assertFalse(authoritative(store, receipt))

    def test_hold_receipt_is_not_authority_and_does_not_read_provider(self):
        store, receipt = self.make()
        receipt["lease_held_by_claimant"] = False
        receipt["decision"] = "HOLD"
        receipt["reason"] = "HELD_BY_OTHER"
        receipt["observed_ref_sha"] = OTHER
        resign(receipt)
        self.assertTrue(verify_receipt(receipt))
        self.assertFalse(authoritative(store, receipt))
        self.assertEqual(store.calls, [])

    def test_sha1_length_preflight_is_never_authoritative(self):
        store = Store()
        receipt = acquire(claim(preflight_sha256="b" * 40), store)
        store.calls.clear()
        with self.assertRaisesRegex(LeaseError, "64 lowercase hex"):
            authoritative(store, receipt, preflight_sha256="b" * 40)


if __name__ == "__main__":
    unittest.main()
