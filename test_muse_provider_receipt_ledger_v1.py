from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys
import types
import unittest
import urllib.parse
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
        self.api_calls = 0
        self.get_tree_calls = 0
        self.contents_reads = 0
        self.receipt_reads = 0
        self.manifest_bytes = 0
        self.compare_rows = 0
        main_tree = self._tree({})
        main = self._commit(main_tree, "0" * 40, "main")
        self.refs["main"] = main

    def reset_work_counters(self):
        self.api_calls = 0
        self.get_tree_calls = 0
        self.contents_reads = 0
        self.receipt_reads = 0
        self.manifest_bytes = 0
        self.compare_rows = 0

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

    def _resolve_commit(self, ref: str) -> str:
        if ref in self.commits:
            return ref
        if ref in self.refs:
            return self.refs[ref]
        raise ledger.MuseProviderReceiptLedgerError("unknown ref")

    def api(self, method, path, *, body=None, token):
        self.api_calls += 1
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
            self.get_tree_calls += 1
            sha = rel.split("/", 2)[2].split("?", 1)[0]
            return {"truncated": False, "tree": [{"path": p, "type": "blob", "sha": b} for p, b in sorted(self.trees[sha].items())]}
        if method == "GET" and rel.startswith("contents/"):
            encoded_path = rel[len("contents/"):]
            encoded_path, query = encoded_path.split("?", 1)
            file_path = urllib.parse.unquote(encoded_path)
            params = urllib.parse.parse_qs(query, strict_parsing=True)
            ref = params["ref"][0]
            commit_sha = self._resolve_commit(ref)
            tree = self.trees[self.commits[commit_sha]["tree"]]
            if file_path not in tree:
                raise ledger.MuseProviderReceiptLedgerError("missing content path")
            blob = tree[file_path]
            raw = self.blobs[blob]
            self.contents_reads += 1
            if file_path == ledger.MANIFEST_PATH:
                self.manifest_bytes += len(raw)
            elif file_path.startswith(ledger.RECEIPT_PREFIX):
                self.receipt_reads += 1
            encoded = base64.b64encode(raw).decode()
            return {"type": "file", "path": file_path, "sha": blob, "encoding": "base64", "content": encoded}
        if method == "GET" and rel.startswith("compare/"):
            span = rel[len("compare/"):]
            base, head = span.split("...", 1)
            base = urllib.parse.unquote(base)
            head = urllib.parse.unquote(head)
            if self.commits[head]["parent"] != base:
                return {"status": "diverged", "ahead_by": 1, "behind_by": 1, "total_commits": 1, "files": []}
            left = self.trees[self.commits[base]["tree"]]
            right = self.trees[self.commits[head]["tree"]]
            files = []
            for name in sorted(set(left) | set(right)):
                if left.get(name) == right.get(name):
                    continue
                status = "added" if name not in left else "removed" if name not in right else "modified"
                files.append({"filename": name, "status": status})
            self.compare_rows += len(files)
            return {"status": "ahead", "ahead_by": 1, "behind_by": 0, "total_commits": 1, "files": files}
        if method == "POST" and rel == "git/trees":
            paths = dict(self.trees[body["base_tree"]])
            for row in body["tree"]:
                paths[row["path"]] = self._blob(row["content"].encode())
            return {"sha": self._tree(paths)}
        if method == "POST" and rel == "git/commits":
            return {"sha": self._commit(body["tree"], body["parents"][0], body["message"])}
        if method == "POST" and rel == "git/refs":
            if body["ref"] != ledger.PROVIDER_REF:
                raise AssertionError(body["ref"])
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

    def generation_commit(self, generation: int) -> str:
        head = self.refs[ledger.PROVIDER_BRANCH]
        while True:
            tree = self.trees[self.commits[head]["tree"]]
            manifest = json.loads(self.blobs[tree[ledger.MANIFEST_PATH]])
            if manifest["generation"] == generation:
                return head
            head = self.commits[head]["parent"]

    def overwrite_manifest(self, generation: int, transform):
        head = self.generation_commit(generation)
        commit = self.commits[head]
        paths = dict(self.trees[commit["tree"]])
        value = transform(json.loads(self.blobs[paths[ledger.MANIFEST_PATH]]))
        paths[ledger.MANIFEST_PATH] = self._blob(ledger._canon(value))
        commit["tree"] = self._tree(paths)

    def inject_current_path(self, path: str, raw: bytes):
        head = self.refs[ledger.PROVIDER_BRANCH]
        commit = self.commits[head]
        paths = dict(self.trees[commit["tree"]])
        paths[path] = self._blob(raw)
        commit["tree"] = self._tree(paths)

    def corrupt_receipt_at_generation(self, generation: int):
        head = self.generation_commit(generation)
        commit = self.commits[head]
        paths = dict(self.trees[commit["tree"]])
        manifest = json.loads(self.blobs[paths[ledger.MANIFEST_PATH]])
        paths[manifest["entry"]["receipt_path"]] = self._blob(b"{}\n")
        commit["tree"] = self._tree(paths)


def candidate(seed: str = "a"):
    chars = "abcdef0123456789"
    offset = chars.index(seed) if seed in chars else 0
    hx = lambda i: chars[(offset + i) % len(chars)] * 64
    seam = hx(6)
    return {
        "buyer_scope_sha256": hx(0), "recipient_fingerprint": hx(1), "offer_scope_sha256": hx(2),
        "route_kind": "EMAIL", "intent_sha256": hx(3), "body_sha256": hx(4),
        "claimant": "Z-LEDGER-TEST", "operation_id": "MUSE-LEDGER-TEST-" + seed,
        "lease_binding": {"schema_version": gate.LEASE_BINDING_SCHEMA, "receipt_schema": gate.LEASE_RECEIPT_SCHEMA,
            "claimant": "Z-LEDGER-TEST", "claim_id": "claim-ledger-" + seed, "seam_sha256": seam,
            "lease_ref": "refs/heads/outbound-lease-v3/" + seam, "lease_commit_sha": "5" * 40,
            "claim_capability_sha256": hx(7), "receipt_sha256": hx(8)},
    }


def request_and_receipt(seed: str = "a"):
    chars = "abcdef0123456789"
    index = chars.index(seed)
    base = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=8)
    request = gate.prepare_request(candidate(seed), request_id="req-ledger-0001-" + seed,
                                   requested_at=base.strftime("%Y-%m-%dT%H:%M:%SZ"))
    ts = f"{int((base + timedelta(seconds=1)).timestamp())}.{index + 1:06d}"
    snapshot = {"schema_version": gate.SNAPSHOT_SCHEMA, "complete": True, "channel_id": gate.MUSE_DM_CONVERSATION_ID,
        "coverage_started_at": (base - timedelta(seconds=600)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "captured_at": (base + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "messages": [{"message_ts": ts, "author_user_id": "U0BSAL3CZ4Y", "text": request["message"]}]}
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
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): self.init()

    def test_append_and_load_exact_remote_receipt(self):
        self.init(); _, receipt = request_and_receipt("a")
        state = ledger.append_receipt(receipt, token=self.token)
        self.assertEqual(state["manifest"]["generation"], 1)
        current_request, _ = request_and_receipt("b")
        proof = ledger.build_request_bound_proof(current_request, token=self.token)
        self.assertTrue(ledger.verify_request_bound_proof(current_request, proof, token=self.token))
        self.assertEqual(ledger.load_prior_receipts(current_request, proof, token=self.token), [receipt])

    def test_current_request_replay_and_duplicate_receipt_fail_closed(self):
        self.init(); request, receipt = request_and_receipt("a")
        ledger.append_receipt(receipt, token=self.token); before = self.provider.refs[ledger.PROVIDER_BRANCH]
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): ledger.build_request_bound_proof(request, token=self.token)
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): ledger.append_receipt(receipt, token=self.token)
        self.assertEqual(self.provider.refs[ledger.PROVIDER_BRANCH], before)

    def test_recomputed_delta_prefix_cannot_detach_from_parent(self):
        self.init(); _, one = request_and_receipt("a"); _, two = request_and_receipt("b")
        ledger.append_receipt(one, token=self.token); ledger.append_receipt(two, token=self.token)
        def attack(manifest):
            manifest["previous_prefix_sha256"] = "f" * 64
            manifest["complete_prefix_sha256"] = ledger._prefix_step(manifest["previous_prefix_sha256"], manifest["entry"])
            return manifest
        self.provider.overwrite_manifest(2, attack)
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): ledger.verify_remote_complete_prefix(token=self.token)

    def test_adjacent_commit_may_change_only_manifest_and_new_receipt(self):
        self.init(); _, receipt = request_and_receipt("a"); ledger.append_receipt(receipt, token=self.token)
        self.provider.inject_current_path("provider/muse_receipt_ledger_v1/foreign.json", b"{}\n")
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): ledger.verify_remote_complete_prefix(token=self.token)

    def test_historical_receipt_corruption_is_detected_at_its_generation(self):
        self.init(); _, one = request_and_receipt("a"); _, two = request_and_receipt("b")
        ledger.append_receipt(one, token=self.token); ledger.append_receipt(two, token=self.token)
        self.provider.corrupt_receipt_at_generation(1)
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): ledger.verify_remote_complete_prefix(token=self.token)

    def test_non_force_cas_rejects_concurrent_sibling(self):
        self.init(); _, receipt = request_and_receipt("a"); self.provider.race_on_patch = True
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): ledger.append_receipt(receipt, token=self.token)
        self.assertEqual(self.provider.force_values, [False])

    def test_old_and_self_hashed_proofs_fail_after_provider_change(self):
        self.init(); request, _ = request_and_receipt("b")
        proof = ledger.build_request_bound_proof(request, token=self.token)
        forged = copy.deepcopy(proof); forged["payload"]["provider_head_sha"] = "f" * 40; forged["proof_sha256"] = ledger._digest(forged["payload"])
        self.assertFalse(ledger.verify_request_bound_proof(request, forged, token=self.token))
        _, receipt = request_and_receipt("a"); ledger.append_receipt(receipt, token=self.token)
        self.assertFalse(ledger.verify_request_bound_proof(request, proof, token=self.token))

    def test_request_candidate_generation_is_exactly_bound(self):
        self.init(); request_a, _ = request_and_receipt("a"); request_b, _ = request_and_receipt("b")
        proof = ledger.build_request_bound_proof(request_a, token=self.token)
        self.assertFalse(ledger.verify_request_bound_proof(request_b, proof, token=self.token))

    def test_unknown_provider_manifest_field_is_rejected(self):
        self.init()
        self.provider.overwrite_manifest(0, lambda manifest: {**manifest, "caller_complete": True})
        with self.assertRaises(ledger.MuseProviderReceiptLedgerError): ledger.verify_remote_complete_prefix(token=self.token)

    def test_provider_token_never_enters_proof(self):
        self.init(); request, _ = request_and_receipt("a")
        proof = ledger.build_request_bound_proof(request, token=self.token)
        self.assertNotIn(self.token, json.dumps(proof, sort_keys=True))

    def test_terminal_composition_requires_current_visible_selected_generation_and_keeps_send_false(self):
        self.init(); request, _ = request_and_receipt("a"); proof = ledger.build_request_bound_proof(request, token=self.token); facts = ledger._request_facts(request)
        slack_receipt = {"payload": {**facts, "schema_version":"outbound-muse-slack-provider-evidence/v1",
            "authority_mode":"PROVIDER_AUTHENTICATED_SLACK_DM_EVIDENCE_V1", "visibility_model":"CURRENT_VISIBLE_SLACK_WEB_API_ONLY",
            "deleted_history_authenticated":False, "requester_control_history_authenticated":False, "prior_receipt_ledger_authenticated":False,
            "terminal_election_authorized":False, "current_visible_effective_observation":"SELECTED", "external_send_authorized":False,
            "side_effects_authorized":False, "requires_current_worker_lease_possession":True, "requires_fresh_provider_preflight":True}}
        fake = types.ModuleType("tools.outbound_send_guard.muse_slack_provider_v1")
        fake.PROVIDER_SCHEMA="outbound-muse-slack-provider-evidence/v1"; fake.AUTHORITY_MODE="PROVIDER_AUTHENTICATED_SLACK_DM_EVIDENCE_V1"; fake.VISIBILITY_MODEL="CURRENT_VISIBLE_SLACK_WEB_API_ONLY"
        fake.verify_provider_evidence=lambda req, rec: req is request and type(rec) is dict and type(rec.get("payload")) is dict
        with mock.patch.dict(sys.modules, {"tools.outbound_send_guard.muse_slack_provider_v1": fake}):
            self.assertTrue(ledger.verify_terminal_coordination(request, slack_receipt, proof, token=self.token))
            unsafe=copy.deepcopy(slack_receipt); unsafe["payload"]["external_send_authorized"]=True
            self.assertFalse(ledger.verify_terminal_coordination(request, unsafe, proof, token=self.token))

    def test_proof_authority_ceiling_is_hard_false(self):
        self.init(); request, _ = request_and_receipt("a"); payload=ledger.build_request_bound_proof(request, token=self.token)["payload"]
        self.assertTrue(payload["prior_receipt_ledger_authenticated"]); self.assertTrue(payload["ledger_complete"])
        self.assertFalse(payload["terminal_election_authorized"]); self.assertFalse(payload["external_send_authorized"]); self.assertFalse(payload["side_effects_authorized"])
        self.assertTrue(payload["requires_current_worker_lease_possession"]); self.assertTrue(payload["requires_fresh_provider_preflight"])


if __name__ == "__main__": unittest.main()
