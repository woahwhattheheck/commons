from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from tools.outbound_send_guard import muse_election_v2 as gate
from tools.outbound_send_guard import muse_provider_receipt_ledger_v1 as ledger


def _sha(raw: bytes) -> str:
    return hashlib.sha1(raw).hexdigest()


def _canon(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


class FakeGitHub:
    def __init__(self):
        self.blobs = {}
        self.trees = {}
        self.commits = {}
        self.refs = {}
        self.force_values = []
        self.race_on_patch = False
        self.truncate_trees = False
        main_tree = self._tree({})
        main = self._commit(main_tree, "0" * 40, "main")
        self.refs["main"] = main

    def _blob(self, raw: bytes) -> str:
        sha = _sha(b"blob\0" + raw)
        self.blobs[sha] = raw
        return sha

    def _tree(self, paths: dict[str, str]) -> str:
        sha = _sha(b"tree\0" + _canon(paths))
        self.trees[sha] = dict(paths)
        return sha

    def _commit(self, tree: str, parent: str, message: str) -> str:
        value = {"tree": tree, "parent": parent, "message": message}
        sha = _sha(b"commit\0" + _canon(value))
        self.commits[sha] = value
        return sha

    def api(self, method, path, *, body=None, token):
        if token != "provider-test-token":
            raise AssertionError("unexpected token")
        prefix = f"/repos/{ledger.PROVIDER_OWNER}/{ledger.PROVIDER_REPO}/"
        if not path.startswith(prefix):
            raise AssertionError(path)
        rel = path[len(prefix):]
        if method == "GET" and rel.startswith("git/ref/heads/"):
            branch = rel[len("git/ref/heads/"):]
            if branch not in self.refs:
                raise ledger.MuseProviderReceiptLedgerError("missing ref")
            return {"object": {"sha": self.refs[branch]}}
        if method == "GET" and rel.startswith("git/commits/"):
            sha = rel.split("/", 2)[2]
            row = self.commits[sha]
            return {"sha": sha, "tree": {"sha": row["tree"]}, "parents": [{"sha": row["parent"]}]}
        if method == "GET" and rel.startswith("git/trees/"):
            sha = rel.split("/", 2)[2].split("?", 1)[0]
            return {
                "truncated": self.truncate_trees,
                "tree": [
                    {"path": path, "type": "blob", "sha": blob}
                    for path, blob in sorted(self.trees[sha].items())
                ],
            }
        if method == "GET" and rel.startswith("git/blobs/"):
            sha = rel.split("/", 2)[2]
            encoded = base64.b64encode(self.blobs[sha]).decode()
            encoded = "\n".join(encoded[i:i + 60] for i in range(0, len(encoded), 60))
            return {"encoding": "base64", "content": encoded}
        if method == "POST" and rel == "git/trees":
            paths = dict(self.trees[body["base_tree"]])
            for row in body["tree"]:
                paths[row["path"]] = self._blob(row["content"].encode())
            return {"sha": self._tree(paths)}
        if method == "POST" and rel == "git/commits":
            return {"sha": self._commit(body["tree"], body["parents"][0], body["message"])}
        if method == "POST" and rel == "git/refs":
            self.assert_equal(body["ref"], ledger.PROVIDER_REF)
            if ledger.PROVIDER_BRANCH in self.refs:
                raise ledger.MuseProviderReceiptLedgerError("ref exists")
            self.refs[ledger.PROVIDER_BRANCH] = body["sha"]
            return {"object": {"sha": body["sha"]}}
        if method == "PATCH" and rel == "git/refs/heads/" + ledger.PROVIDER_BRANCH:
            self.force_values.append(body.get("force"))
            current = self.refs[ledger.PROVIDER_BRANCH]
            if self.race_on_patch:
                row = self.commits[current]
                sibling = self._commit(row["tree"], current, "foreign sibling")
                self.refs[ledger.PROVIDER_BRANCH] = sibling
                current = sibling
                self.race_on_patch = False
            target = body["sha"]
            if body.get("force") is not False or self.commits[target]["parent"] != current:
                raise ledger.MuseProviderReceiptLedgerError("non-fast-forward CAS rejected")
            self.refs[ledger.PROVIDER_BRANCH] = target
            return {"object": {"sha": target}}
        raise AssertionError((method, rel, body))

    @staticmethod
    def assert_equal(left, right):
        if left != right:
            raise AssertionError((left, right))

    def overwrite_current_manifest(self, transform):
        head = self.refs[ledger.PROVIDER_BRANCH]
        commit = self.commits[head]
        paths = dict(self.trees[commit["tree"]])
        raw = self.blobs[paths[ledger.MANIFEST_PATH]]
        value = transform(json.loads(raw))
        paths[ledger.MANIFEST_PATH] = self._blob(ledger._canon(value))
        commit["tree"] = self._tree(paths)


def candidate(seed: str = "a"):
    chars = "abcdef0123456789"
    offset = chars.index(seed) if seed in chars else 0
    hx = lambda i: chars[(offset + i) % len(chars)] * 64
    seam = hx(6)
    return {
        "buyer_scope_sha256": hx(0),
        "recipient_fingerprint": hx(1),
        "offer_scope_sha256": hx(2),
        "route_kind": "EMAIL",
        "intent_sha256": hx(3),
        "body_sha256": hx(4),
        "claimant": "Z-LEDGER-TEST",
        "operation_id": "MUSE-LEDGER-TEST-" + seed,
        "lease_binding": {
            "schema_version": gate.LEASE_BINDING_SCHEMA,
            "receipt_schema": gate.LEASE_RECEIPT_SCHEMA,
            "claimant": "Z-LEDGER-TEST",
            "claim_id": "claim-ledger-" + seed,
            "seam_sha256": seam,
            "lease_ref": "refs/heads/outbound-lease-v3/" + seam,
            "lease_commit_sha": "5" * 40,
            "claim_capability_sha256": hx(7),
            "receipt_sha256": hx(8),
        },
    }


def request_and_receipt(seed: str = "a"):
    base = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=8)
    requested = base.strftime("%Y-%m-%dT%H:%M:%SZ")
    request = gate.prepare_request(
        candidate(seed),
        request_id="req-ledger-0001-" + seed,
        requested_at=requested,
    )
    ts = f"{int((base + timedelta(seconds=1)).timestamp())}.000001"
    snapshot = {
        "schema_version": gate.SNAPSHOT_SCHEMA,
        "complete": True,
        "channel_id": gate.MUSE_DM_CONVERSATION_ID,
        "coverage_started_at": (base - timedelta(seconds=600)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "captured_at": (base + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "messages": [
            {"message_ts": ts, "author_user_id": "U0BSAL3CZ4Y", "text": request["message"]}
        ],
    }
    receipt = gate.compile_receipt(request, snapshot, prior_receipts=(), ledger_complete=True)
    if not gate.verify_receipt(receipt):
        raise AssertionError("fixture receipt failed canonical verification")
    return request, receipt


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeGitHub()
        self.patch = mock.patch.object(ledger, "_api", side_effect=self.provider.api)
        self.patch.start()
        self.token = "provider-test-token"

    def tearDown(self):
        self.patch.stop()

    def init(self):
        return ledger.initialize_remote_ledger(token=self.token)

    def test_init_is_exclusive_and_generation_zero_is_provider_verified(self):
        state = self.init()
        self.assertEqual(state["manifest"]["generation"], 0)
        self.assertEqual(state["manifest"]["entries"], [])
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError):
            self.init()

    def test_append_and_load_exact_remote_receipt(self):
        self.init()
        _, receipt = request_and_receipt("a")
        state = ledger.append_receipt(receipt, token=self.token)
        self.assertEqual(state["manifest"]["generation"], 1)
        current_request, _ = request_and_receipt("b")
        proof = ledger.build_request_bound_proof(current_request, token=self.token)
        self.assertTrue(ledger.verify_request_bound_proof(current_request, proof, token=self.token))
        self.assertEqual(ledger.load_prior_receipts(current_request, proof, token=self.token), [receipt])

    def test_current_request_replay_cannot_receive_complete_prior_proof(self):
        self.init()
        request, receipt = request_and_receipt("a")
        ledger.append_receipt(receipt, token=self.token)
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError):
            ledger.build_request_bound_proof(request, token=self.token)

    def test_remint_duplicate_receipt_is_rejected_without_head_movement(self):
        self.init()
        _, receipt = request_and_receipt("a")
        ledger.append_receipt(receipt, token=self.token)
        before = self.provider.refs[ledger.PROVIDER_BRANCH]
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError):
            ledger.append_receipt(receipt, token=self.token)
        self.assertEqual(self.provider.refs[ledger.PROVIDER_BRANCH], before)

    def test_reordered_prefix_is_rejected_even_with_recomputed_local_hash(self):
        self.init()
        _, one = request_and_receipt("a")
        _, two = request_and_receipt("b")
        ledger.append_receipt(one, token=self.token)
        ledger.append_receipt(two, token=self.token)

        def attack(manifest):
            rows = list(reversed(manifest["entries"]))
            for index, row in enumerate(rows):
                row["ordinal"] = index
            manifest["entries"] = rows
            manifest["complete_prefix_sha256"] = ledger._prefix_digest(rows)
            return manifest

        self.provider.overwrite_current_manifest(attack)
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError):
            ledger.verify_remote_complete_prefix(token=self.token)

    def test_missing_provider_tree_page_fails_closed(self):
        self.init()
        self.provider.truncate_trees = True
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError):
            ledger.verify_remote_complete_prefix(token=self.token)

    def test_non_force_cas_rejects_concurrent_sibling(self):
        self.init()
        _, receipt = request_and_receipt("a")
        self.provider.race_on_patch = True
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError):
            ledger.append_receipt(receipt, token=self.token)
        self.assertEqual(self.provider.force_values, [False])

    def test_old_proof_fails_after_legitimate_head_advance(self):
        self.init()
        request, _ = request_and_receipt("b")
        proof = ledger.build_request_bound_proof(request, token=self.token)
        _, receipt = request_and_receipt("a")
        ledger.append_receipt(receipt, token=self.token)
        self.assertFalse(ledger.verify_request_bound_proof(request, proof, token=self.token))

    def test_self_hashed_caller_proof_cannot_override_provider_head(self):
        self.init()
        request, _ = request_and_receipt("b")
        proof = ledger.build_request_bound_proof(request, token=self.token)
        forged = copy.deepcopy(proof)
        forged["payload"]["provider_head_sha"] = "f" * 40
        forged["proof_sha256"] = ledger._digest(forged["payload"])
        self.assertFalse(ledger.verify_request_bound_proof(request, forged, token=self.token))

    def test_request_candidate_generation_is_exactly_bound(self):
        self.init()
        request_a, _ = request_and_receipt("a")
        request_b, _ = request_and_receipt("b")
        proof = ledger.build_request_bound_proof(request_a, token=self.token)
        self.assertFalse(ledger.verify_request_bound_proof(request_b, proof, token=self.token))

    def test_unknown_manifest_field_is_rejected(self):
        self.init()

        def attack(manifest):
            manifest["caller_complete"] = True
            return manifest

        self.provider.overwrite_current_manifest(attack)
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError):
            ledger.verify_remote_complete_prefix(token=self.token)

    def test_provider_token_never_enters_proof(self):
        self.init()
        request, _ = request_and_receipt("a")
        proof = ledger.build_request_bound_proof(request, token=self.token)
        self.assertNotIn(self.token, json.dumps(proof, sort_keys=True))

    def test_terminal_composition_requires_same_selected_slack_generation_and_keeps_send_false(self):
        self.init()
        request, _ = request_and_receipt("a")
        proof = ledger.build_request_bound_proof(request, token=self.token)
        facts = ledger._request_facts(request)
        slack_receipt = {
            "payload": {
                **facts,
                "effective_observation": "SELECTED",
                "external_send_authorized": False,
                "side_effects_authorized": False,
                "requires_current_worker_lease_possession": True,
                "requires_fresh_provider_preflight": True,
            }
        }
        fake = types.ModuleType("tools.outbound_send_guard.muse_slack_provider_v1")
        fake.verify_provider_evidence = lambda req, rec: req is request and rec is slack_receipt
        name = "tools.outbound_send_guard.muse_slack_provider_v1"
        with mock.patch.dict(sys.modules, {name: fake}):
            self.assertTrue(
                ledger.verify_terminal_coordination(request, slack_receipt, proof, token=self.token)
            )
            bad = copy.deepcopy(slack_receipt)
            bad["payload"]["candidate_sha256"] = "f" * 64
            self.assertFalse(
                ledger.verify_terminal_coordination(request, bad, proof, token=self.token)
            )
            unsafe = copy.deepcopy(slack_receipt)
            unsafe["payload"]["external_send_authorized"] = True
            self.assertFalse(
                ledger.verify_terminal_coordination(request, unsafe, proof, token=self.token)
            )

    def test_proof_authority_ceiling_is_hard_false(self):
        self.init()
        request, _ = request_and_receipt("a")
        payload = ledger.build_request_bound_proof(request, token=self.token)["payload"]
        self.assertTrue(payload["prior_receipt_ledger_authenticated"])
        self.assertTrue(payload["ledger_complete"])
        self.assertFalse(payload["terminal_election_authorized"])
        self.assertFalse(payload["external_send_authorized"])
        self.assertFalse(payload["side_effects_authorized"])
        self.assertTrue(payload["requires_current_worker_lease_possession"])
        self.assertTrue(payload["requires_fresh_provider_preflight"])


if __name__ == "__main__":
    unittest.main()
