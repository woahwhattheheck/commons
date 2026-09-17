#!/usr/bin/env python3
"""Provider-authenticated append-only complete-prefix ledger for Muse v2 receipts."""
from __future__ import annotations

import argparse, base64, hashlib, json, os, re, sys, urllib.error, urllib.parse, urllib.request
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
HEX40_64_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ENTRY_FIELDS = {"schema_version","ordinal","receipt_sha256","receipt_path","request_sha256","request_id","publication_key","candidate_sha256","decision","compiled_at","selection_message_ts"}
MANIFEST_FIELDS = {"schema_version","provider_repo","provider_ref","generation","genesis_parent_sha","previous_head_sha","entries","complete_prefix_sha256"}
PROOF_FIELDS = {"schema_version","provider_repo","provider_ref","provider_head_sha","generation","entry_count","complete_prefix_sha256","manifest_sha256","request_sha256","request_id","publication_key","candidate_sha256","prior_receipt_ledger_authenticated","ledger_complete","terminal_election_authorized","requires_current_worker_lease_possession","requires_fresh_provider_preflight","external_send_authorized","side_effects_authorized"}

class MuseProviderReceiptLedgerError(ValueError):
    pass


def _strict_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out: raise MuseProviderReceiptLedgerError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _parse_json_bytes(raw: bytes, label: str) -> Any:
    if type(raw) is not bytes: raise MuseProviderReceiptLedgerError(f"{label}: bytes required")
    try: text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc: raise MuseProviderReceiptLedgerError(f"{label}: UTF-8 required") from exc
    try:
        return json.loads(text, object_pairs_hook=_strict_pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(MuseProviderReceiptLedgerError(f"{label}: non-finite {x}")))
    except MuseProviderReceiptLedgerError: raise
    except json.JSONDecodeError as exc: raise MuseProviderReceiptLedgerError(f"{label}: invalid JSON") from exc


def _canon(value: Any) -> bytes:
    try: text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc: raise MuseProviderReceiptLedgerError("value is not canonical JSON") from exc
    return (text + "\n").encode()


def _digest(value: Any) -> str: return hashlib.sha256(_canon(value)).hexdigest()

def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not HEX40_64_RE.fullmatch(value): raise MuseProviderReceiptLedgerError(f"{label}: Git object id required")
    return value

def _hex64(value: Any, label: str) -> str:
    if type(value) is not str or not HEX64_RE.fullmatch(value): raise MuseProviderReceiptLedgerError(f"{label}: SHA-256 required")
    return value

def _text(value: Any, label: str, max_len: int = 256) -> str:
    if type(value) is not str or not value or len(value) > max_len or any(ord(c) < 0x20 or ord(c) == 0x7f for c in value):
        raise MuseProviderReceiptLedgerError(f"{label}: bounded printable string required")
    return value

def _uint(value: Any, label: str, limit: int) -> int:
    if type(value) is bool or type(value) is not int or value < 0 or value > limit: raise MuseProviderReceiptLedgerError(f"{label}: integer out of range")
    return value

def _exact(obj: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(obj) is not dict or set(obj) != fields: raise MuseProviderReceiptLedgerError(f"{label}: exact fields required")
    return obj


def _token() -> str:
    value = os.environ.get(TOKEN_ENV)
    if type(value) is not str or not value or len(value) > 4096 or any(ord(c) < 0x21 or ord(c) > 0x7e for c in value):
        raise MuseProviderReceiptLedgerError(f"{TOKEN_ENV}: printable token required")
    return value


def _api(method: str, path: str, *, body: Mapping[str, Any] | None = None, token: str) -> Any:
    if method not in {"GET","POST","PATCH"}: raise MuseProviderReceiptLedgerError("unsupported provider method")
    if not path.startswith(f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/"): raise MuseProviderReceiptLedgerError("provider path escaped fixed repository")
    req = urllib.request.Request(PROVIDER_API + path, data=None if body is None else _canon(body),
        headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,"Content-Type":"application/json","X-GitHub-Api-Version":"2022-11-28"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response: raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc: raise MuseProviderReceiptLedgerError(f"GitHub {method} {path}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc: raise MuseProviderReceiptLedgerError(f"GitHub {method} {path}: transport failure") from exc
    if len(raw) > MAX_RESPONSE_BYTES: raise MuseProviderReceiptLedgerError("provider response too large")
    if not raw: return {}
    try: return json.loads(raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise MuseProviderReceiptLedgerError("provider returned invalid JSON") from exc


def _get_ref(token: str) -> str:
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/ref/heads/{PROVIDER_BRANCH}", token=token)
    try: return _sha(value["object"]["sha"], "provider ref sha")
    except (KeyError, TypeError) as exc: raise MuseProviderReceiptLedgerError("malformed provider ref") from exc

def _get_default_head(token: str) -> str:
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/ref/heads/main", token=token)
    try: return _sha(value["object"]["sha"], "main ref sha")
    except (KeyError, TypeError) as exc: raise MuseProviderReceiptLedgerError("malformed main ref") from exc

def _get_commit(token: str, sha: str) -> dict[str, str]:
    sha = _sha(sha, "commit sha")
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/commits/{sha}", token=token)
    try:
        tree = _sha(value["tree"]["sha"], "tree sha"); parents = [_sha(x["sha"], "parent sha") for x in value["parents"]]
    except (KeyError, TypeError) as exc: raise MuseProviderReceiptLedgerError("malformed provider commit") from exc
    if len(parents) != 1: raise MuseProviderReceiptLedgerError("ledger commit must have one parent")
    return {"sha": sha, "tree_sha": tree, "parent_sha": parents[0]}

def _get_tree(token: str, sha: str) -> dict[str, str]:
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/trees/{_sha(sha,'tree sha')}?recursive=1", token=token)
    if type(value) is not dict or value.get("truncated") is True or type(value.get("tree")) is not list: raise MuseProviderReceiptLedgerError("provider tree incomplete/malformed")
    out = {}
    for row in value["tree"]:
        if type(row) is dict and row.get("type") == "blob": out[_text(row.get("path"),"tree path",4096)] = _sha(row.get("sha"),"blob sha")
    return out

def _get_blob(token: str, sha: str) -> bytes:
    value = _api("GET", f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/blobs/{_sha(sha,'blob sha')}", token=token)
    if type(value) is not dict or value.get("encoding") != "base64" or type(value.get("content")) is not str: raise MuseProviderReceiptLedgerError("provider blob malformed")
    try: return base64.b64decode("".join(value["content"].split()), validate=True)
    except (ValueError, TypeError) as exc: raise MuseProviderReceiptLedgerError("provider blob invalid base64") from exc


def _receipt_path(sha: str) -> str: return RECEIPT_PREFIX + _hex64(sha,"receipt sha256") + ".json"
def _prefix_digest(entries) -> str: return _digest({"schema_version":PREFIX_SCHEMA,"entries":entries})
def _manifest(generation: int, genesis: str, previous: str | None, entries: list[Mapping[str,Any]]) -> dict[str,Any]:
    return {"schema_version":LEDGER_SCHEMA,"provider_repo":PROVIDER_REPO_FULL_NAME,"provider_ref":PROVIDER_REF,"generation":generation,"genesis_parent_sha":_sha(genesis,"genesis sha"),"previous_head_sha":previous,"entries":list(entries),"complete_prefix_sha256":_prefix_digest(list(entries))}


def _request_facts(request: Mapping[str,Any]) -> dict[str,str]:
    try: payload, request_sha, _ = gate._validate_request(request)
    except (KeyError, TypeError, ValueError) as exc: raise MuseProviderReceiptLedgerError("request: canonical v2 verification failed") from exc
    return {"request_sha256":_hex64(request_sha,"request sha"),"request_id":_text(payload["request_id"],"request id",160),"publication_key":_hex64(payload["publication_key"],"publication key"),"candidate_sha256":_hex64(payload["candidate_sha256"],"candidate sha")}


def _receipt_facts(receipt: Mapping[str,Any]) -> dict[str,Any]:
    if not gate.verify_receipt(receipt) or type(receipt) is not dict or set(receipt) != {"payload","receipt_sha256"}: raise MuseProviderReceiptLedgerError("canonical Muse v2 receipt required")
    p = receipt["payload"]; raw = _canon(receipt); decision = p.get("decision"); selection = p.get("selection_message_ts")
    if decision not in {"SELECTED","NOT_SELECTED","HOLD"} or (selection is not None and type(selection) is not str): raise MuseProviderReceiptLedgerError("receipt metadata invalid")
    return {"receipt_bytes":raw,"receipt_sha256":hashlib.sha256(raw).hexdigest(),"request_sha256":_hex64(p.get("request_sha256"),"receipt request sha"),"request_id":_text(p.get("request_id"),"receipt request id",160),"publication_key":_hex64(p.get("publication_key"),"receipt publication key"),"candidate_sha256":_hex64(p.get("candidate_sha256"),"receipt candidate sha"),"decision":decision,"compiled_at":_text(p.get("compiled_at"),"compiled at",32),"selection_message_ts":selection}


def _entry(facts: Mapping[str,Any], ordinal: int) -> dict[str,Any]:
    _uint(ordinal,"ordinal",MAX_ENTRIES-1)
    return {"schema_version":ENTRY_SCHEMA,"ordinal":ordinal,"receipt_sha256":facts["receipt_sha256"],"receipt_path":_receipt_path(facts["receipt_sha256"]),"request_sha256":facts["request_sha256"],"request_id":facts["request_id"],"publication_key":facts["publication_key"],"candidate_sha256":facts["candidate_sha256"],"decision":facts["decision"],"compiled_at":facts["compiled_at"],"selection_message_ts":facts["selection_message_ts"]}


def _validate_entry(raw: Any, ordinal: int) -> dict[str,Any]:
    row = _exact(raw,ENTRY_FIELDS,f"entry[{ordinal}]"); _uint(row["ordinal"],f"entry[{ordinal}].ordinal",MAX_ENTRIES-1)
    if row["schema_version"] != ENTRY_SCHEMA or row["ordinal"] != ordinal: raise MuseProviderReceiptLedgerError("entry schema/ordinal mismatch")
    out = {"schema_version":ENTRY_SCHEMA,"ordinal":ordinal,"receipt_sha256":_hex64(row["receipt_sha256"],"receipt sha"),"receipt_path":_text(row["receipt_path"],"receipt path",512),"request_sha256":_hex64(row["request_sha256"],"request sha"),"request_id":_text(row["request_id"],"request id",160),"publication_key":_hex64(row["publication_key"],"publication key"),"candidate_sha256":_hex64(row["candidate_sha256"],"candidate sha"),"decision":row["decision"],"compiled_at":_text(row["compiled_at"],"compiled at",32),"selection_message_ts":row["selection_message_ts"]}
    if out["receipt_path"] != _receipt_path(out["receipt_sha256"]) or out["decision"] not in {"SELECTED","NOT_SELECTED","HOLD"} or (out["selection_message_ts"] is not None and type(out["selection_message_ts"]) is not str): raise MuseProviderReceiptLedgerError("entry metadata invalid")
    return out


def _validate_manifest(raw: Any) -> dict[str,Any]:
    value = _exact(raw,MANIFEST_FIELDS,"manifest")
    if value["schema_version"] != LEDGER_SCHEMA or value["provider_repo"] != PROVIDER_REPO_FULL_NAME or value["provider_ref"] != PROVIDER_REF: raise MuseProviderReceiptLedgerError("manifest identity mismatch")
    generation = _uint(value["generation"],"generation",MAX_ENTRIES); rows = value["entries"]
    if type(rows) is not list or len(rows) != generation: raise MuseProviderReceiptLedgerError("manifest generation mismatch")
    entries = [_validate_entry(row,i) for i,row in enumerate(rows)]; genesis = _sha(value["genesis_parent_sha"],"genesis sha")
    previous = value["previous_head_sha"]
    if generation == 0:
        if previous is not None: raise MuseProviderReceiptLedgerError("generation zero previous head must be null")
    else: previous = _sha(previous,"previous head")
    if _hex64(value["complete_prefix_sha256"],"prefix sha") != _prefix_digest(entries): raise MuseProviderReceiptLedgerError("prefix digest mismatch")
    for field in ("receipt_sha256","request_sha256"):
        vals=[e[field] for e in entries]
        if len(vals)!=len(set(vals)): raise MuseProviderReceiptLedgerError(f"duplicate {field}")
    pairs=[(e["request_id"],e["candidate_sha256"]) for e in entries]
    if len(pairs)!=len(set(pairs)): raise MuseProviderReceiptLedgerError("duplicate request generation")
    selected=[e["selection_message_ts"] for e in entries if e["selection_message_ts"] is not None]
    if len(selected)!=len(set(selected)): raise MuseProviderReceiptLedgerError("duplicate selection evidence")
    return _manifest(generation,genesis,previous,entries)


def _read_generation(token: str, head: str):
    commit=_get_commit(token,head); tree=_get_tree(token,commit["tree_sha"]); receipt_paths={p for p in tree if p.startswith(RECEIPT_PREFIX)}
    if any(p.startswith("provider/muse_receipt_ledger_v1/") and p!=MANIFEST_PATH and p not in receipt_paths for p in tree): raise MuseProviderReceiptLedgerError("undeclared ledger file")
    blob=tree.get(MANIFEST_PATH)
    if blob is None: raise MuseProviderReceiptLedgerError("manifest missing")
    raw=_get_blob(token,blob); value=_parse_json_bytes(raw,"manifest")
    if _canon(value)!=raw: raise MuseProviderReceiptLedgerError("manifest not canonical")
    manifest=_validate_manifest(value); declared={e["receipt_path"] for e in manifest["entries"]}
    if declared!=receipt_paths: raise MuseProviderReceiptLedgerError("receipt object set mismatch")
    for entry in manifest["entries"]:
        rraw=_get_blob(token,tree[entry["receipt_path"]]); obj=_parse_json_bytes(rraw,entry["receipt_path"])
        if _canon(obj)!=rraw or hashlib.sha256(rraw).hexdigest()!=entry["receipt_sha256"]: raise MuseProviderReceiptLedgerError("receipt bytes/digest mismatch")
        facts=_receipt_facts(obj)
        for key in ("receipt_sha256","request_sha256","request_id","publication_key","candidate_sha256","decision","compiled_at","selection_message_ts"):
            if facts[key]!=entry[key]: raise MuseProviderReceiptLedgerError(f"receipt metadata mismatch: {key}")
    return manifest,commit,tree


def verify_remote_complete_prefix(*, token: str|None=None) -> dict[str,Any]:
    token=_token() if token is None else token; start=_get_ref(token); head=start; newer=None; current=None
    for _ in range(MAX_ENTRIES+1):
        manifest,commit,_tree=_read_generation(token,head); current=current or manifest
        if newer is not None:
            if newer["previous_head_sha"]!=head or newer["generation"]!=manifest["generation"]+1 or newer["genesis_parent_sha"]!=manifest["genesis_parent_sha"] or newer["entries"][:-1]!=manifest["entries"]: raise MuseProviderReceiptLedgerError("non-append ledger history")
        if manifest["generation"]==0:
            if commit["parent_sha"]!=manifest["genesis_parent_sha"]: raise MuseProviderReceiptLedgerError("genesis parent mismatch")
            break
        if commit["parent_sha"]!=manifest["previous_head_sha"]: raise MuseProviderReceiptLedgerError("commit/manifest parent mismatch")
        newer=manifest; head=commit["parent_sha"]
    else: raise MuseProviderReceiptLedgerError("ledger chain too long")
    if _get_ref(token)!=start: raise MuseProviderReceiptLedgerError("provider head changed during verification")
    return {"provider_head_sha":start,"manifest":current}


def _post_tree(token: str, base: str, files: Mapping[str,bytes]) -> str:
    rows=[{"path":p,"mode":"100644","type":"blob","content":raw.decode("utf-8","strict")} for p,raw in sorted(files.items())]
    value=_api("POST",f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/trees",body={"base_tree":_sha(base,"base tree"),"tree":rows},token=token)
    try:return _sha(value["sha"],"created tree")
    except (KeyError,TypeError) as exc: raise MuseProviderReceiptLedgerError("create-tree malformed") from exc

def _post_commit(token: str, tree: str, parent: str, generation: int) -> str:
    value=_api("POST",f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/commits",body={"message":f"Muse receipt ledger generation {generation}","tree":_sha(tree,"tree"),"parents":[_sha(parent,"parent")]},token=token)
    try:return _sha(value["sha"],"created commit")
    except (KeyError,TypeError) as exc: raise MuseProviderReceiptLedgerError("create-commit malformed") from exc


def initialize_remote_ledger(*, token: str|None=None) -> dict[str,Any]:
    token=_token() if token is None else token; genesis=_get_default_head(token); base=_get_commit(token,genesis); manifest=_manifest(0,genesis,None,[])
    tree=_post_tree(token,base["tree_sha"],{MANIFEST_PATH:_canon(manifest)}); commit=_post_commit(token,tree,genesis,0)
    value=_api("POST",f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/refs",body={"ref":PROVIDER_REF,"sha":commit},token=token)
    try: observed=_sha(value["object"]["sha"],"created ref")
    except (KeyError,TypeError) as exc: raise MuseProviderReceiptLedgerError("create-ref malformed") from exc
    if observed!=commit or _get_ref(token)!=commit: raise MuseProviderReceiptLedgerError("exclusive ref readback mismatch")
    return verify_remote_complete_prefix(token=token)


def append_receipt(receipt: Mapping[str,Any], *, token: str|None=None) -> dict[str,Any]:
    token=_token() if token is None else token; state=verify_remote_complete_prefix(token=token); old=state["provider_head_sha"]; manifest=state["manifest"]
    facts=_receipt_facts(receipt); entry=_entry(facts,manifest["generation"]); new=_validate_manifest(_manifest(manifest["generation"]+1,manifest["genesis_parent_sha"],old,manifest["entries"]+[entry]))
    base=_get_commit(token,old); tree=_post_tree(token,base["tree_sha"],{entry["receipt_path"]:facts["receipt_bytes"],MANIFEST_PATH:_canon(new)}); commit=_post_commit(token,tree,old,new["generation"])
    _api("PATCH",f"/repos/{PROVIDER_OWNER}/{PROVIDER_REPO}/git/refs/heads/{PROVIDER_BRANCH}",body={"sha":commit,"force":False},token=token)
    if _get_ref(token)!=commit: raise MuseProviderReceiptLedgerError("provider CAS/readback mismatch")
    return verify_remote_complete_prefix(token=token)


def build_request_bound_proof(request: Mapping[str,Any], *, token: str|None=None) -> dict[str,Any]:
    token=_token() if token is None else token; req=_request_facts(request); state=verify_remote_complete_prefix(token=token); manifest=state["manifest"]
    if any(e["request_sha256"]==req["request_sha256"] for e in manifest["entries"]): raise MuseProviderReceiptLedgerError("current request already in prior ledger")
    payload={"schema_version":PROOF_SCHEMA,"provider_repo":PROVIDER_REPO_FULL_NAME,"provider_ref":PROVIDER_REF,"provider_head_sha":state["provider_head_sha"],"generation":manifest["generation"],"entry_count":len(manifest["entries"]),"complete_prefix_sha256":manifest["complete_prefix_sha256"],"manifest_sha256":_digest(manifest),**req,"prior_receipt_ledger_authenticated":True,"ledger_complete":True,"terminal_election_authorized":False,"requires_current_worker_lease_possession":True,"requires_fresh_provider_preflight":True,"external_send_authorized":False,"side_effects_authorized":False}
    return {"payload":payload,"proof_sha256":_digest(payload)}


def verify_request_bound_proof(request: Mapping[str,Any], proof: Mapping[str,Any], *, token: str|None=None) -> bool:
    try:
        if type(proof) is not dict or set(proof)!={"payload","proof_sha256"}: return False
        p=_exact(proof["payload"],PROOF_FIELDS,"proof"); _sha(p["provider_head_sha"],"proof head"); _uint(p["generation"],"proof generation",MAX_ENTRIES); _uint(p["entry_count"],"proof entry count",MAX_ENTRIES)
        for key in ("complete_prefix_sha256","manifest_sha256","request_sha256","publication_key","candidate_sha256"): _hex64(p[key],f"proof {key}")
        _text(p["request_id"],"proof request id",160)
        if p["schema_version"]!=PROOF_SCHEMA or p["provider_repo"]!=PROVIDER_REPO_FULL_NAME or p["provider_ref"]!=PROVIDER_REF or proof["proof_sha256"]!=_digest(p): return False
        if p["prior_receipt_ledger_authenticated"] is not True or p["ledger_complete"] is not True or p["terminal_election_authorized"] is not False or p["requires_current_worker_lease_possession"] is not True or p["requires_fresh_provider_preflight"] is not True or p["external_send_authorized"] is not False or p["side_effects_authorized"] is not False: return False
        req=_request_facts(request)
        if any(p[k]!=req[k] for k in req): return False
        token=_token() if token is None else token
        return build_request_bound_proof(request,token=token)==proof
    except (MuseProviderReceiptLedgerError,KeyError,TypeError,ValueError,OSError): return False


def load_prior_receipts(request: Mapping[str,Any], proof: Mapping[str,Any], *, token: str|None=None):
    token=_token() if token is None else token
    if not verify_request_bound_proof(request,proof,token=token): raise MuseProviderReceiptLedgerError("ledger proof is not current")
    state=verify_remote_complete_prefix(token=token)
    if state["provider_head_sha"]!=proof["payload"]["provider_head_sha"]: raise MuseProviderReceiptLedgerError("provider head changed")
    tree=_get_tree(token,_get_commit(token,state["provider_head_sha"])["tree_sha"]); out=[_parse_json_bytes(_get_blob(token,tree[e["receipt_path"]]),e["receipt_path"]) for e in state["manifest"]["entries"]]
    if _get_ref(token)!=state["provider_head_sha"]: raise MuseProviderReceiptLedgerError("provider head changed during load")
    return out


def verify_terminal_coordination(request: Mapping[str,Any], slack_provider_receipt: Mapping[str,Any], ledger_proof: Mapping[str,Any], *, token: str|None=None) -> bool:
    try: from tools.outbound_send_guard import muse_slack_provider_v1 as slack_provider
    except ImportError: return False
    try:
        if not slack_provider.verify_provider_evidence(request,slack_provider_receipt) or not verify_request_bound_proof(request,ledger_proof,token=token): return False
        req=_request_facts(request); sp=slack_provider_receipt.get("payload"); lp=ledger_proof.get("payload")
        if type(sp) is not dict or type(lp) is not dict or sp.get("effective_observation")!="SELECTED": return False
        if any(sp.get(k)!=req[k] or lp.get(k)!=req[k] for k in req): return False
        for p in (sp,lp):
            if p.get("external_send_authorized") is not False or p.get("side_effects_authorized") is not False or p.get("requires_current_worker_lease_possession") is not True or p.get("requires_fresh_provider_preflight") is not True: return False
        return True
    except (MuseProviderReceiptLedgerError,KeyError,TypeError,ValueError,OSError): return False


def _read(path: str, label: str):
    try:
        with open(path,"rb") as f: return _parse_json_bytes(f.read(),label)
    except OSError as exc: raise MuseProviderReceiptLedgerError(f"{label}: read failed") from exc
def _write(value): sys.stdout.buffer.write(_canon(value))
def _parser():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="command",required=True); sub.add_parser("init")
    a=sub.add_parser("append"); a.add_argument("--receipt",required=True); q=sub.add_parser("proof"); q.add_argument("--request",required=True); v=sub.add_parser("verify-proof"); v.add_argument("--request",required=True); v.add_argument("--proof",required=True); return p

def main(argv=None):
    args=_parser().parse_args(argv)
    try:
        if args.command=="init": _write(initialize_remote_ledger()); return 0
        if args.command=="append": _write(append_receipt(_read(args.receipt,"receipt"))); return 0
        if args.command=="proof": _write(build_request_bound_proof(_read(args.request,"request"))); return 0
        ok=verify_request_bound_proof(_read(args.request,"request"),_read(args.proof,"proof")); _write({"valid":ok}); return 0 if ok else 2
    except (MuseProviderReceiptLedgerError,OSError,KeyError,TypeError,ValueError) as exc: print(f"ERROR: {exc}",file=sys.stderr); return 2

if __name__ == "__main__": raise SystemExit(main())
