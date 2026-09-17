#!/usr/bin/env python3
"""Provider-authenticated append-only complete-prefix ledger for Muse v2 receipts.

GitHub is the fixed provider. The reviewed writer is the only supported mutation
surface and advances a fixed ref by non-force compare-and-swap. Verification
re-reads the remote ref, every retained generation, and every immutable receipt
object; local files, paths, filenames, self-hashes, or a caller completeness
boolean carry no authority.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

from tools.outbound_send_guard import muse_election_v2 as gate

PROVIDER_OWNER = "woahwhattheheck"
PROVIDER_REPO = "commons"
PROVIDER_REPO_FULL_NAME = PROVIDER_OWNER + "/" + PROVIDER_REPO
PROVIDER_API = "https://api.github.com"
PROVIDER_REF = "refs/heads/muse-provider-receipt-ledger-v1"
PROVIDER_BRANCH = "muse-provider-receipt-ledger-v1"
TOKEN_ENV = "MUSE_LEDGER_GITHUB_TOKEN"

LEDGER_SCHEMA = "outbound-muse-provider-receipt-ledger/v1"
ENTRY_SCHEMA = "outbound-muse-provider-receipt-ledger-entry/v1"
PROOF_SCHEMA = "outbound-muse-provider-receipt-ledger-proof/v1"
PREFIX_SCHEMA = "outbound-muse-provider-receipt-ledger-prefix/v1"
MANIFEST_PATH = "provider/muse_receipt_ledger_v1/manifest.json"
RECEIPT_PREFIX = "provider/muse_receipt_ledger_v1/receipts/"
MAX_ENTRIES = 4096
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_CHAIN = MAX_ENTRIES + 1
HEX40_64_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class MuseProviderReceiptLedgerError(ValueError):
    pass


def _strict_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise MuseProviderReceiptLedgerError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _parse_json_bytes(raw: bytes, label: str) -> Any:
    if type(raw) is not bytes:
        raise MuseProviderReceiptLedgerError(f"{label}: bytes required")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise MuseProviderReceiptLedgerError(f"{label}: UTF-8 required") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                MuseProviderReceiptLedgerError(f"{label}: non-finite {token}")
            ),
        )
    except MuseProviderReceiptLedgerError:
        raise
    except json.JSONDecodeError as exc:
        raise MuseProviderReceiptLedgerError(f"{label}: invalid JSON") from exc


def _canon(value: Any) -> bytes:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise MuseProviderReceiptLedgerError("value is not canonical JSON") from exc
    return (text + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not HEX40_64_RE.fullmatch(value):
        raise MuseProviderReceiptLedgerError(f"{label}: Git object id required")
    return value


def _hex64(value: Any, label: str) -> str:
    if type(value) is not str or not HEX64_RE.fullmatch(value):
        raise MuseProviderReceiptLedgerError(f"{label}: SHA-256 required")
    return value


def _text(value: Any, label: str, *, max_len: int = 256) -> str:
    if type(value) is not str or not value or len(value) > max_len:
        raise MuseProviderReceiptLedgerError(f"{label}: bounded nonempty string required")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise MuseProviderReceiptLedgerError(f"{label}: control character forbidden")
    return value


def _exact(obj: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(obj) is not dict:
        raise MuseProviderReceiptLedgerError(f"{label}: object required")
    if set(obj) != fields:
        raise MuseProviderReceiptLedgerError(f"{label}: exact fields required")
    return obj


def _token() -> str:
    value = os.environ.get(TOKEN_ENV)
    if type(value) is not str or not value or len(value) > 4096:
        raise MuseProviderReceiptLedgerError(f"{TOKEN_ENV}: token required")
    if any(ord(ch) < 0x21 or ord(ch) > 0x7E for ch in value):
        raise MuseProviderReceiptLedgerError(f"{TOKEN_ENV}: printable token required")
    return value


def _api(method: str, path: str, *, body: Mapping[str, Any] | None = None, token: str) -> Any:
    """Fixed-host GitHub REST transport. Tests replace this function."""
    if method not in {"GET", "POST", "PATCH"}:
        raise MuseProviderReceiptLedgerError("unsupported provider method")
    if not path.startswith(f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/"):
        raise MuseProviderReceiptLedgerError("provider path escaped fixed repository")
    data = None if body is None else _canon(body)
    request = urllib.request.Request(
        PROVIDER_API + path,
        data=data,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise MuseProviderReceiptLedgerError(f"GitHub {method} {path}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise MuseProviderReceiptLedgerError(f"GitHub {method} {path}: transport failure") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise MuseProviderReceiptLedgerError("provider response too large")
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MuseProviderReceiptLedgerError("provider returned invalid JSON") from exc


def _get_ref(token: str, ref: str = PROVIDER_REF) -> str:
    if ref != PROVIDER_REF:
        raise MuseProviderReceiptLedgerError("only fixed ledger ref is supported")
    encoded = urllib.parse.quote(PROVIDER_BRANCH, safe="")
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/ref/heads/{encoded}", token=token)
    try:
        return _sha(value["object"]["sha"], "provider ref sha")
    except (KeyError, TypeError) as exc:
        raise MuseProviderReceiptLedgerError("malformed provider ref") from exc


def _get_default_head(token: str) -> str:
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/ref/heads/main", token=token)
    try:
        return _sha(value["object"]["sha"], "main ref sha")
    except (KeyError, TypeError) as exc:
        raise MuseProviderReceiptLedgerError("malformed main ref") from exc


def _get_commit(token: str, sha: str) -> dict[str, Any]:
    sha = _sha(sha, "commit sha")
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/commits/{sha}", token=token)
    if type(value) is not dict:
        raise MuseProviderReceiptLedgerError("malformed provider commit")
    try:
        tree_sha = _sha(value["tree"]["sha"], "tree sha")
        parents = [_sha(row["sha"], "parent sha") for row in value["parents"]]
    except (KeyError, TypeError) as exc:
        raise MuseProviderReceiptLedgerError("malformed provider commit") from exc
    if len(parents) != 1:
        raise MuseProviderReceiptLedgerError("ledger commits require exactly one parent")
    return {"sha": sha, "tree_sha": tree_sha, "parent_sha": parents[0]}


def _get_tree(token: str, tree_sha: str) -> dict[str, str]:
    tree_sha = _sha(tree_sha, "tree sha")
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/trees/{tree_sha}?recursive=1", token=token)
    if type(value) is not dict or value.get("truncated") is True:
        raise MuseProviderReceiptLedgerError("provider tree incomplete")
    rows = value.get("tree")
    if type(rows) is not list:
        raise MuseProviderReceiptLedgerError("provider tree malformed")
    result: dict[str, str] = {}
    for row in rows:
        if type(row) is not dict or row.get("type") != "blob":
            continue
        path = row.get("path")
        sha = row.get("sha")
        if type(path) is not str:
            raise MuseProviderReceiptLedgerError("provider tree path malformed")
        result[path] = _sha(sha, "blob sha")
    return result


def _get_blob(token: str, blob_sha: str) -> bytes:
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/blobs/{_sha(blob_sha, 'blob sha')}", token=token)
    if type(value) is not dict or value.get("encoding") != "base64" or type(value.get("content")) is not str:
        raise MuseProviderReceiptLedgerError("provider blob malformed")
    try:
        compact = "".join(value["content"].split())
        return base64.b64decode(compact, validate=True)
    except (ValueError, TypeError) as exc:
        raise MuseProviderReceiptLedgerError("provider blob invalid base64") from exc


def _receipt_path(receipt_sha256: str) -> str:
    return RECEIPT_PREFIX + _hex64(receipt_sha256, "receipt sha256") + ".json"

ENTRY_FIELDS = {"schema_version", "ordinal", "receipt_sha256", "receipt_path", "request_sha256", "request_id", "publication_key", "candidate_sha256", "decision", "compiled_at", "selection_message_ts"}
MANIFEST_FIELDS = {"schema_version", "provider_repo", "provider_ref", "generation", "genesis_parent_sha", "previous_head_sha", "entries", "complete_prefix_sha256"}
PROOF_FIELDS = {"schema_version", "provider_repo", "provider_ref", "provider_head_sha", "generation", "entry_count", "complete_prefix_sha256", "manifest_sha256", "request_sha256", "request_id", "publication_key", "candidate_sha256", "prior_receipt_ledger_authenticated", "ledger_complete", "terminal_election_authorized", "requires_current_worker_lease_possession", "requires_fresh_provider_preflight", "external_send_authorized", "side_effects_authorized"}


def _request_facts(request: Mapping[str, Any]) -> dict[str, str]:
    try:
        payload, request_sha, _ = gate._validate_request(request)
    except (KeyError, TypeError, ValueError) as exc:
        raise MuseProviderReceiptLedgerError("request: canonical v2 verification failed") from exc
    return {
        "request_sha256": _hex64(request_sha, "request.request_sha256"),
        "request_id": _text(payload["request_id"], "request.request_id", max_len=160),
        "publication_key": _hex64(payload["publication_key"], "request.publication_key"),
        "candidate_sha256": _hex64(payload["candidate_sha256"], "request.candidate_sha256"),
    }


def _receipt_facts(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not gate.verify_receipt(receipt):
        raise MuseProviderReceiptLedgerError("receipt: canonical Muse v2 verification failed")
    if type(receipt) is not dict or set(receipt) != {"payload", "receipt_sha256"}:
        raise MuseProviderReceiptLedgerError("receipt: exact envelope required")
    payload = receipt["payload"]
    if type(payload) is not dict:
        raise MuseProviderReceiptLedgerError("receipt.payload: object required")
    receipt_bytes = _canon(receipt)
    object_sha = hashlib.sha256(receipt_bytes).hexdigest()
    decision = payload.get("decision")
    if decision not in {"SELECTED", "NOT_SELECTED", "HOLD"}:
        raise MuseProviderReceiptLedgerError("receipt.decision invalid")
    selection_ts = payload.get("selection_message_ts")
    if selection_ts is not None and type(selection_ts) is not str:
        raise MuseProviderReceiptLedgerError("receipt.selection_message_ts invalid")
    return {
        "receipt_bytes": receipt_bytes,
        "receipt_sha256": object_sha,
        "request_sha256": _hex64(payload.get("request_sha256"), "receipt.request_sha256"),
        "request_id": _text(payload.get("request_id"), "receipt.request_id", max_len=160),
        "publication_key": _hex64(payload.get("publication_key"), "receipt.publication_key"),
        "candidate_sha256": _hex64(payload.get("candidate_sha256"), "receipt.candidate_sha256"),
        "decision": decision,
        "compiled_at": _text(payload.get("compiled_at"), "receipt.compiled_at", max_len=32),
        "selection_message_ts": selection_ts,
    }


def _entry(facts: Mapping[str, Any], ordinal: int) -> dict[str, Any]:
    if type(ordinal) is bool or type(ordinal) is not int or ordinal < 0 or ordinal >= MAX_ENTRIES:
        raise MuseProviderReceiptLedgerError("entry ordinal out of range")
    return {"schema_version": ENTRY_SCHEMA, "ordinal": ordinal, "receipt_sha256": facts["receipt_sha256"], "receipt_path": _receipt_path(facts["receipt_sha256"]), "request_sha256": facts["request_sha256"], "request_id": facts["request_id"], "publication_key": facts["publication_key"], "candidate_sha256": facts["candidate_sha256"], "decision": facts["decision"], "compiled_at": facts["compiled_at"], "selection_message_ts": facts["selection_message_ts"]}


def _prefix_digest(entries: list[Mapping[str, Any]]) -> str:
    return _digest({"schema_version": PREFIX_SCHEMA, "entries": entries})


def _manifest(*, generation: int, genesis_parent_sha: str, previous_head_sha: str | None, entries: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {"schema_version": LEDGER_SCHEMA, "provider_repo": PROVIDER_REPO_FULL_NAME, "provider_ref": PROVIDER_REF, "generation": generation, "genesis_parent_sha": _sha(genesis_parent_sha, "genesis parent sha"), "previous_head_sha": previous_head_sha, "entries": list(entries), "complete_prefix_sha256": _prefix_digest(list(entries))}


def _validate_entry(raw: Any, ordinal: int) -> dict[str, Any]:
    row = _exact(raw, ENTRY_FIELDS, f"entry[{ordinal}]")
    if row["schema_version"] != ENTRY_SCHEMA or row["ordinal"] != ordinal:
        raise MuseProviderReceiptLedgerError(f"entry[{ordinal}]: schema/ordinal mismatch")
    normalized = {"schema_version": ENTRY_SCHEMA, "ordinal": ordinal, "receipt_sha256": _hex64(row["receipt_sha256"], f"entry[{ordinal}].receipt_sha256"), "receipt_path": _text(row["receipt_path"], f"entry[{ordinal}].receipt_path", max_len=512), "request_sha256": _hex64(row["request_sha256"], f"entry[{ordinal}].request_sha256"), "request_id": _text(row["request_id"], f"entry[{ordinal}].request_id", max_len=160), "publication_key": _hex64(row["publication_key"], f"entry[{ordinal}].publication_key"), "candidate_sha256": _hex64(row["candidate_sha256"], f"entry[{ordinal}].candidate_sha256"), "decision": row["decision"], "compiled_at": _text(row["compiled_at"], f"entry[{ordinal}].compiled_at", max_len=32), "selection_message_ts": row["selection_message_ts"]}
    if normalized["receipt_path"] != _receipt_path(normalized["receipt_sha256"]):
        raise MuseProviderReceiptLedgerError(f"entry[{ordinal}]: receipt path not digest-derived")
    if normalized["decision"] not in {"SELECTED", "NOT_SELECTED", "HOLD"}:
        raise MuseProviderReceiptLedgerError(f"entry[{ordinal}]: decision invalid")
    if normalized["selection_message_ts"] is not None and type(normalized["selection_message_ts"]) is not str:
        raise MuseProviderReceiptLedgerError(f"entry[{ordinal}]: selection timestamp invalid")
    return normalized


def _validate_manifest(raw: Any) -> dict[str, Any]:
    value = _exact(raw, MANIFEST_FIELDS, "manifest")
    if value["schema_version"] != LEDGER_SCHEMA or value["provider_repo"] != PROVIDER_REPO_FULL_NAME or value["provider_ref"] != PROVIDER_REF:
        raise MuseProviderReceiptLedgerError("manifest identity/schema mismatch")
    generation = value["generation"]
    if type(generation) is bool or type(generation) is not int or generation < 0 or generation > MAX_ENTRIES:
        raise MuseProviderReceiptLedgerError("manifest generation invalid")
    rows = value["entries"]
    if type(rows) is not list or len(rows) != generation or len(rows) > MAX_ENTRIES:
        raise MuseProviderReceiptLedgerError("manifest entries/generation mismatch")
    entries = [_validate_entry(row, i) for i, row in enumerate(rows)]
    genesis = _sha(value["genesis_parent_sha"], "manifest.genesis_parent_sha")
    previous = value["previous_head_sha"]
    if generation == 0:
        if previous is not None:
            raise MuseProviderReceiptLedgerError("generation zero previous head must be null")
    else:
        previous = _sha(previous, "manifest.previous_head_sha")
    prefix = _hex64(value["complete_prefix_sha256"], "manifest.complete_prefix_sha256")
    if prefix != _prefix_digest(entries):
        raise MuseProviderReceiptLedgerError("manifest complete-prefix digest mismatch")
    for field in ("receipt_sha256", "request_sha256"):
        vals = [row[field] for row in entries]
        if len(vals) != len(set(vals)):
            raise MuseProviderReceiptLedgerError(f"manifest duplicate {field}")
    pairs = [(row["request_id"], row["candidate_sha256"]) for row in entries]
    if len(pairs) != len(set(pairs)):
        raise MuseProviderReceiptLedgerError("manifest duplicate request/candidate generation")
    selected_ts = [row["selection_message_ts"] for row in entries if row["selection_message_ts"] is not None]
    if len(selected_ts) != len(set(selected_ts)):
        raise MuseProviderReceiptLedgerError("manifest duplicate selection evidence")
    return _manifest(generation=generation, genesis_parent_sha=genesis, previous_head_sha=previous, entries=entries)


def _read_generation(token: str, head_sha: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    commit = _get_commit(token, head_sha)
    tree = _get_tree(token, commit["tree_sha"])
    prefix_paths = {path for path in tree if path.startswith(RECEIPT_PREFIX)}
    unexpected = {path for path in tree if path.startswith("provider/muse_receipt_ledger_v1/") and path != MANIFEST_PATH and path not in prefix_paths}
    if unexpected:
        raise MuseProviderReceiptLedgerError("ledger tree contains undeclared provider files")
    manifest_blob = tree.get(MANIFEST_PATH)
    if manifest_blob is None:
        raise MuseProviderReceiptLedgerError("ledger manifest missing")
    manifest_raw = _get_blob(token, manifest_blob)
    manifest_value = _parse_json_bytes(manifest_raw, "manifest")
    if _canon(manifest_value) != manifest_raw:
        raise MuseProviderReceiptLedgerError("manifest bytes are not canonical")
    manifest = _validate_manifest(manifest_value)
    declared = {row["receipt_path"] for row in manifest["entries"]}
    if prefix_paths != declared:
        raise MuseProviderReceiptLedgerError("receipt object set does not exactly match manifest")
    for row in manifest["entries"]:
        raw = _get_blob(token, tree[row["receipt_path"]])
        value = _parse_json_bytes(raw, row["receipt_path"])
        if _canon(value) != raw:
            raise MuseProviderReceiptLedgerError("receipt object bytes are not canonical")
        if hashlib.sha256(raw).hexdigest() != row["receipt_sha256"]:
            raise MuseProviderReceiptLedgerError("receipt object digest mismatch")
        facts = _receipt_facts(value)
        for key in ("receipt_sha256", "request_sha256", "request_id", "publication_key", "candidate_sha256", "decision", "compiled_at", "selection_message_ts"):
            if facts[key] != row[key]:
                raise MuseProviderReceiptLedgerError(f"receipt object metadata mismatch: {key}")
    return manifest, commit, tree


def verify_remote_complete_prefix(*, token: str | None = None) -> dict[str, Any]:
    token = _token() if token is None else token
    start_head = _get_ref(token)
    head = start_head
    expected_next: dict[str, Any] | None = None
    current: dict[str, Any] | None = None
    for depth in range(MAX_CHAIN):
        manifest, commit, _ = _read_generation(token, head)
        if depth == 0:
            current = manifest
        if expected_next is not None:
            if expected_next["previous_head_sha"] != head or expected_next["generation"] != manifest["generation"] + 1:
                raise MuseProviderReceiptLedgerError("generation chain mismatch")
            if expected_next["genesis_parent_sha"] != manifest["genesis_parent_sha"] or expected_next["entries"][:-1] != manifest["entries"]:
                raise MuseProviderReceiptLedgerError("ledger is not an exact append-only prefix")
        if manifest["generation"] == 0:
            if commit["parent_sha"] != manifest["genesis_parent_sha"]:
                raise MuseProviderReceiptLedgerError("generation zero parent mismatch")
            break
        if commit["parent_sha"] != manifest["previous_head_sha"]:
            raise MuseProviderReceiptLedgerError("commit parent does not match manifest previous head")
        expected_next = manifest
        head = commit["parent_sha"]
    else:
        raise MuseProviderReceiptLedgerError("ledger chain exceeds bound")
    if current is None:
        raise MuseProviderReceiptLedgerError("ledger current generation missing")
    if _get_ref(token) != start_head:
        raise MuseProviderReceiptLedgerError("provider head changed during verification")
    return {"provider_head_sha": start_head, "manifest": current}


def _post_tree(token: str, *, base_tree_sha: str, files: Mapping[str, bytes]) -> str:
    tree_rows = [{"path": path, "mode": "100644", "type": "blob", "content": raw.decode("utf-8", "strict")} for path, raw in sorted(files.items())]
    value = _api("POST", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/trees", body={"base_tree": _sha(base_tree_sha, "base tree sha"), "tree": tree_rows}, token=token)
    try:
        return _sha(value["sha"], "created tree sha")
    except (KeyError, TypeError) as exc:
        raise MuseProviderReceiptLedgerError("provider create-tree malformed") from exc


def _post_commit(token: str, *, tree_sha: str, parent_sha: str, generation: int) -> str:
    value = _api("POST", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/commits", body={"message": f"Muse receipt ledger generation {generation}", "tree": _sha(tree_sha, "tree sha"), "parents": [_sha(parent_sha, "parent sha")]}, token=token)
    try:
        return _sha(value["sha"], "created commit sha")
    except (KeyError, TypeError) as exc:
        raise MuseProviderReceiptLedgerError("provider create-commit malformed") from exc


def initialize_remote_ledger(*, token: str | None = None) -> dict[str, Any]:
    token = _token() if token is None else token
    genesis = _get_default_head(token)
    base_commit = _get_commit(token, genesis)
    manifest = _manifest(generation=0, genesis_parent_sha=genesis, previous_head_sha=None, entries=[])
    tree_sha = _post_tree(token, base_tree_sha=base_commit["tree_sha"], files={MANIFEST_PATH: _canon(manifest)})
    commit_sha = _post_commit(token, tree_sha=tree_sha, parent_sha=genesis, generation=0)
    value = _api("POST", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/refs", body={"ref": PROVIDER_REF, "sha": commit_sha}, token=token)
    try:
        observed = _sha(value["object"]["sha"], "created ref sha")
    except (KeyError, TypeError) as exc:
        raise MuseProviderReceiptLedgerError("provider create-ref malformed") from exc
    if observed != commit_sha or _get_ref(token) != commit_sha:
        raise MuseProviderReceiptLedgerError("exclusive ref creation readback mismatch")
    return verify_remote_complete_prefix(token=token)


def append_receipt(receipt: Mapping[str, Any], *, token: str | None = None) -> dict[str, Any]:
    token = _token() if token is None else token
    state = verify_remote_complete_prefix(token=token)
    old_head = state["provider_head_sha"]
    manifest = state["manifest"]
    facts = _receipt_facts(receipt)
    new_entry = _entry(facts, manifest["generation"])
    new_manifest = _validate_manifest(_manifest(generation=manifest["generation"] + 1, genesis_parent_sha=manifest["genesis_parent_sha"], previous_head_sha=old_head, entries=manifest["entries"] + [new_entry]))
    old_commit = _get_commit(token, old_head)
    tree_sha = _post_tree(token, base_tree_sha=old_commit["tree_sha"], files={new_entry["receipt_path"]: facts["receipt_bytes"], MANIFEST_PATH: _canon(new_manifest)})
    commit_sha = _post_commit(token, tree_sha=tree_sha, parent_sha=old_head, generation=new_manifest["generation"])
    _api("PATCH", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/refs/heads/{urllib.parse.quote(PROVIDER_BRANCH, safe='')}", body={"sha": commit_sha, "force": False}, token=token)
    if _get_ref(token) != commit_sha:
        raise MuseProviderReceiptLedgerError("provider CAS/readback did not land exact commit")
    return verify_remote_complete_prefix(token=token)


def build_request_bound_proof(request: Mapping[str, Any], *, token: str | None = None) -> dict[str, Any]:
    token = _token() if token is None else token
    req = _request_facts(request)
    state = verify_remote_complete_prefix(token=token)
    manifest = state["manifest"]
    if any(row["request_sha256"] == req["request_sha256"] for row in manifest["entries"]):
        raise MuseProviderReceiptLedgerError("current request already exists in prior-receipt ledger")
    payload = {"schema_version": PROOF_SCHEMA, "provider_repo": PROVIDER_REPO_FULL_NAME, "provider_ref": PROVIDER_REF, "provider_head_sha": state["provider_head_sha"], "generation": manifest["generation"], "entry_count": len(manifest["entries"]), "complete_prefix_sha256": manifest["complete_prefix_sha256"], "manifest_sha256": _digest(manifest), **req, "prior_receipt_ledger_authenticated": True, "ledger_complete": True, "terminal_election_authorized": False, "requires_current_worker_lease_possession": True, "requires_fresh_provider_preflight": True, "external_send_authorized": False, "side_effects_authorized": False}
    return {"payload": payload, "proof_sha256": _digest(payload)}


def verify_request_bound_proof(request: Mapping[str, Any], proof: Mapping[str, Any], *, token: str | None = None) -> bool:
    try:
        if type(proof) is not dict or set(proof) != {"payload", "proof_sha256"}:
            return False
        payload = _exact(proof["payload"], PROOF_FIELDS, "proof.payload")
        if payload["schema_version"] != PROOF_SCHEMA or payload["provider_repo"] != PROVIDER_REPO_FULL_NAME or payload["provider_ref"] != PROVIDER_REF or proof["proof_sha256"] != _digest(payload):
            return False
        if payload["prior_receipt_ledger_authenticated"] is not True or payload["ledger_complete"] is not True or payload["terminal_election_authorized"] is not False:
            return False
        if payload["requires_current_worker_lease_possession"] is not True or payload["requires_fresh_provider_preflight"] is not True or payload["external_send_authorized"] is not False or payload["side_effects_authorized"] is not False:
            return False
        req = _request_facts(request)
        if any(payload[key] != req[key] for key in req):
            return False
        token = _token() if token is None else token
        return build_request_bound_proof(request, token=token) == proof
    except (MuseProviderReceiptLedgerError, KeyError, TypeError, ValueError, OSError):
        return False


def load_prior_receipts(request: Mapping[str, Any], proof: Mapping[str, Any], *, token: str | None = None) -> list[Mapping[str, Any]]:
    token = _token() if token is None else token
    if not verify_request_bound_proof(request, proof, token=token):
        raise MuseProviderReceiptLedgerError("request-bound ledger proof is not current")
    state = verify_remote_complete_prefix(token=token)
    manifest = state["manifest"]
    if state["provider_head_sha"] != proof["payload"]["provider_head_sha"]:
        raise MuseProviderReceiptLedgerError("provider head changed after proof verification")
    commit = _get_commit(token, state["provider_head_sha"])
    tree = _get_tree(token, commit["tree_sha"])
    receipts = [_parse_json_bytes(_get_blob(token, tree[row["receipt_path"]]), row["receipt_path"]) for row in manifest["entries"]]
    if _get_ref(token) != state["provider_head_sha"]:
        raise MuseProviderReceiptLedgerError("provider head changed during receipt load")
    return receipts


def verify_terminal_coordination(request: Mapping[str, Any], slack_provider_receipt: Mapping[str, Any], ledger_proof: Mapping[str, Any], *, token: str | None = None) -> bool:
    try:
        from tools.outbound_send_guard import muse_slack_provider_v1 as slack_provider
    except ImportError:
        return False
    try:
        if not slack_provider.verify_provider_evidence(request, slack_provider_receipt) or not verify_request_bound_proof(request, ledger_proof, token=token):
            return False
        req = _request_facts(request)
        sp = slack_provider_receipt.get("payload")
        lp = ledger_proof.get("payload")
        if type(sp) is not dict or type(lp) is not dict:
            return False
        for key in ("request_sha256", "request_id", "publication_key", "candidate_sha256"):
            if sp.get(key) != req[key] or lp.get(key) != req[key]:
                return False
        if sp.get("effective_observation") != "SELECTED":
            return False
        for payload in (sp, lp):
            if payload.get("external_send_authorized") is not False or payload.get("side_effects_authorized") is not False or payload.get("requires_current_worker_lease_possession") is not True or payload.get("requires_fresh_provider_preflight") is not True:
                return False
        return True
    except (MuseProviderReceiptLedgerError, KeyError, TypeError, ValueError, OSError):
        return False


def _read_json(path: str, label: str) -> Any:
    try:
        with open(path, "rb") as handle:
            return _parse_json_bytes(handle.read(), label)
    except OSError as exc:
        raise MuseProviderReceiptLedgerError(f"{label}: read failed") from exc


def _write_json(value: Any) -> None:
    sys.stdout.buffer.write(_canon(value))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    a = sub.add_parser("append")
    a.add_argument("--receipt", required=True)
    pr = sub.add_parser("proof")
    pr.add_argument("--request", required=True)
    vp = sub.add_parser("verify-proof")
    vp.add_argument("--request", required=True)
    vp.add_argument("--proof", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            _write_json(initialize_remote_ledger())
            return 0
        if args.command == "append":
            _write_json(append_receipt(_read_json(args.receipt, "receipt")))
            return 0
        if args.command == "proof":
            _write_json(build_request_bound_proof(_read_json(args.request, "request")))
            return 0
        ok = verify_request_bound_proof(_read_json(args.request, "request"), _read_json(args.proof, "proof"))
        _write_json({"valid": ok})
        return 0 if ok else 2
    except (MuseProviderReceiptLedgerError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
