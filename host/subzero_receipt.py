#!/usr/bin/env python3
"""host/subzero_receipt.py — quote-draft → buyer-bound receipt.

Slack 1787650230.035359 (JOJO BACKEND CELL H-008) landed the
first binder. Slack 1787650970.236559 / 1787651030.360809
(H-009 + second-pass audit) measured concrete defects on squash
5d79607990fb1493464940a5763a658742a230fd / tree
0509da3e5be25020433bfdeb8883fc6fc97e8986. This leftover hardens
that same binder. Do not remint H-008.

Measured defects:
- inbound_rel rejected / but not Windows \\, so ..\\ground\\EXECUTE
  escaped p/ on Windows
- any existing p/{id}.md counted as BUYER_BOUND; the self-check
  used the project's own quote receipt as buyer_id
- missing numeric fields coerced to 0 with int(... or 0)
- no source commit/tree, quote/row/request/delivery hashes, or
  DRAFT→NEEDS_BUYER→ACCEPTED→DELIVERED transitions
- PASS refused only for hard-coded GRBN
- titan NOT_WRITTEN / hands-off titan --go framed as a lock

File existence is not buyer acceptance. Missing numbers stay
UNRESOLVED / FINDER-FAILED, never a silent 0. Live bind stays
UNBOUND. Cash stays $0 / NOT_LANDED. Demand stays UNKNOWN.
Bound is still STRUCTURAL_ONLY. No auth. No gate.

Do not remint SUBZERO_QUOTE / SUBZERO_GTM / SUBZERO_BUYERS /
SUBZERO_EXPLORER / SUBZERO_PROOF / White Box / payment-ready /
human-outcomes / grok-receipt / PR 2320 /
rivet-ship-subzero-receipt-20260825-01. Do not open accounts.
Do not message buyers. Do not store bank, routing, card, tax,
or private-buyer data. Do not smash commons.mno.

X = Slack H-008 + H-009 second-pass + quote leftover + GTM sku
    + P01 + schema + leftover paths.
Y = inbound-id canonicalization + missing-field UNRESOLVED +
    quote/row/request hashes + legal transitions + project
    receipt is not a buyer.
Z = missing leftover / invented buyer / cash-runtime-demand
    claim / FINDER-FAILED / FINDER-UNVERIFIED. Never 0.

  python3 host/subzero_receipt.py
  python3 host/subzero_receipt.py --root .
  python3 host/subzero_receipt.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "SUBZERO_RECEIPT.json")
DEFAULT_CARD = os.path.join("ground", "SUBZERO_RECEIPT.md")
DEFAULT_DOOR = "subzero-receipt.html"
DEFAULT_QUOTE = os.path.join("ground", "SUBZERO_QUOTE.json")
DEFAULT_ARCH = os.path.join("revenue", "subzero_gtm", "architecture.json")
DEFAULT_BUYERS = os.path.join("revenue", "subzero_buyers", "pack.json")
DEFAULT_SCHEMA = os.path.join(
    "revenue", "subzero_buyers", "validation_receipt.schema.json"
)
SLACK_TS = "1787650230.035359"
AUDIT_SLACK_TS = "1787651030.360809"
RECONCILE_SLACK_TS = "1787650970.236559"
CELL = "H-008"
AUDIT_CELL = "H-009"
SKU_ID = "sz-paid-validation"
P01_ID = "P01_catalog_receipt"
QUOTE_PRICE = 2500
QUOTE_RECEIPT = "rivet-ship-subzero-quote-20260825-01"
HUMAN_RECEIPT = "rivet-ship-human-outcomes-20260825-01"
H008_RECEIPT = "rivet-ship-subzero-receipt-20260825-01"
GRBN_REL = os.path.join("excerpts", "20260823", "muhl_grbn.mno")
HDVS_REL = os.path.join("excerpts", "20260823", "muhl_hdvs.mno")
GRBN_SHA = "09214540b3f3117ab93a4c509017a5e7b9c5f12d86545069af4ffcdae99c6632"
AUDITED_COMMIT = "5d79607990fb1493464940a5763a658742a230fd"
AUDITED_TREE = "0509da3e5be25020433bfdeb8883fc6fc97e8986"
POST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
PROJECT_NOT_BUYER = frozenset(
    {
        QUOTE_RECEIPT,
        HUMAN_RECEIPT,
        H008_RECEIPT,
    }
)
LEGAL_TRANSITIONS = {
    "DRAFT": frozenset({"NEEDS_BUYER"}),
    "NEEDS_BUYER": frozenset({"ACCEPTED", "DRAFT"}),
    "ACCEPTED": frozenset({"DELIVERED"}),
    "DELIVERED": frozenset(),
}
SEARCH_SPACE = (
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    os.path.join("host", "subzero_receipt.py"),
    DEFAULT_DOOR,
    DEFAULT_QUOTE,
    DEFAULT_ARCH,
    DEFAULT_BUYERS,
    DEFAULT_SCHEMA,
    os.path.join("host", "subzero_quote.py"),
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
    os.path.join("p", QUOTE_RECEIPT + ".md"),
)
CALIBRATION = (
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
ALREADY_LANDED = (
    os.path.join("host", "subzero_quote.py"),
    os.path.join("ground", "SUBZERO_QUOTE.md"),
    os.path.join("ground", "SUBZERO_QUOTE.json"),
    DEFAULT_ARCH,
    DEFAULT_BUYERS,
    DEFAULT_SCHEMA,
    os.path.join("host", "subzero_explorer.py"),
    os.path.join("host", "human_outcomes.py"),
    os.path.join("p", QUOTE_RECEIPT + ".md"),
    os.path.join("p", H008_RECEIPT + ".md"),
)
REQUIRED_PHRASES = (
    "sz-paid-validation",
    "p01_catalog_receipt",
    "quote-draft",
    "buyer-bound",
    "validation receipt",
    "1787650230.035359",
    "1787651030.360809",
    "h-008",
    "h-009",
    "structural_only",
    "not runtime",
    "not demand",
    "not cash",
    "unbound",
    "unresolved",
    "finder-failed",
    "finder-unverified",
    "never 0",
    "open door",
    "unseated",
    "no auth",
    "no gate",
    "talk is not a land",
    "project receipt is not a buyer",
    "file is not acceptance",
    "quote hash",
    "source tree",
    "needs_buyer",
)
HEX64 = set("0123456789abcdef")


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _read_bytes(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return b""


def _exists(root, rel):
    return os.path.isfile(os.path.join(root, rel))


def _hex_sha(value):
    text = str(value or "").strip().lower()
    return len(text) == 64 and set(text) <= HEX64


def file_sha(root, rel):
    blob = _read_bytes(root, rel)
    if not blob:
        return ""
    return hashlib.sha256(blob).hexdigest()


def parse_excerpt(blob):
    """Read magic + LE header. Short or empty is FINDER-FAILED."""
    if len(blob) < 28:
        return {"ok": False, "reason": "header too short", "sha256": ""}
    magic = blob[:8].decode("ascii", "replace")
    n_gate, n_wires, n_in, n_out, depth = struct.unpack_from("<IIIII", blob, 8)
    return {
        "ok": True,
        "reason": "",
        "magic": magic,
        "n_gate": n_gate,
        "n_wires": n_wires,
        "n_in": n_in,
        "n_out": n_out,
        "depth": depth,
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def load_json(text, label):
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": label + " is not JSON"}
    if not isinstance(data, dict):
        return {"error": label + " is not an object"}
    return data


def present_int(obj, key):
    """Missing / empty / bool / unparseable is UNRESOLVED, never coerced 0."""
    if not isinstance(obj, dict) or key not in obj:
        return None
    value = obj.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def field_state(value):
    return "PRESENT" if value is not None else "UNRESOLVED"


def source_index(root):
    """Read already-landed quote / GTM / P01 / schema. Do not remint."""
    quote = load_json(_read(root, DEFAULT_QUOTE), "quote")
    arch = load_json(_read(root, DEFAULT_ARCH), "architecture")
    buyers = load_json(_read(root, DEFAULT_BUYERS), "buyers")
    schema = load_json(_read(root, DEFAULT_SCHEMA), "schema")
    sku = quote.get("sku") if isinstance(quote.get("sku"), dict) else {}
    evidence = quote.get("evidence") if isinstance(quote.get("evidence"), dict) else {}
    arch_sku = {}
    for item in arch.get("paths") or []:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == SKU_ID:
            arch_sku = item
            break
    p01 = {}
    for item in buyers.get("paths") or []:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == P01_ID:
            p01 = item
            break
    defs = schema.get("$defs") if isinstance(schema.get("$defs"), dict) else {}
    quote_price = present_int(sku, "price_usd")
    arch_price = present_int(arch_sku, "price_usd")
    p01_from = present_int(p01, "price_usd_from")
    p01_to = present_int(p01, "price_usd_to")
    structural_only = present_int(evidence, "structural_only")
    runtime_measured = present_int(evidence, "runtime_measured")
    customer_ready = present_int(evidence, "customer_ready")
    collected_cash = present_int(quote, "collected_cash_usd")
    quote_hash = file_sha(root, DEFAULT_QUOTE)
    row_payload = json.dumps(sku, sort_keys=True, separators=(",", ":")).encode("utf-8")
    catalog_row_hash = hashlib.sha256(row_payload).hexdigest() if sku else ""
    return {
        "quote_error": str(quote.get("error") or ""),
        "arch_error": str(arch.get("error") or ""),
        "buyers_error": str(buyers.get("error") or ""),
        "schema_error": str(schema.get("error") or ""),
        "sku_id": str(sku.get("id") or "").strip(),
        "quote_class": str(sku.get("class") or "").strip().upper(),
        "quote_price": quote_price,
        "quote_price_state": field_state(quote_price),
        "quote_status": str(sku.get("status") or "").strip().upper(),
        "quote_hash": quote_hash,
        "catalog_row_hash": catalog_row_hash,
        "arch_id": str(arch_sku.get("id") or "").strip(),
        "arch_price": arch_price,
        "arch_price_state": field_state(arch_price),
        "arch_status": str(arch_sku.get("status") or "").strip().upper(),
        "arch_implements": str(arch_sku.get("implements") or "").strip(),
        "p01_id": str(p01.get("id") or "").strip(),
        "p01_from": p01_from,
        "p01_from_state": field_state(p01_from),
        "p01_to": p01_to,
        "p01_to_state": field_state(p01_to),
        "schema_has_buyer": "buyer_receipt" in defs,
        "schema_no_auth": schema.get("no_auth") is True,
        "schema_no_gate": schema.get("no_gate") is True,
        "structural_only": structural_only,
        "structural_only_state": field_state(structural_only),
        "runtime_measured": runtime_measured,
        "runtime_measured_state": field_state(runtime_measured),
        "customer_ready": customer_ready,
        "customer_ready_state": field_state(customer_ready),
        "runtime_proof": bool(evidence.get("runtime_proof")) if "runtime_proof" in evidence else None,
        "collected_cash_usd": collected_cash,
        "collected_cash_state": field_state(collected_cash),
        "cash_state": str(quote.get("cash_state") or "").strip().upper(),
        "demand": str(quote.get("demand") or "").strip().upper(),
    }


def inbound_rel(inbound_id, root=None):
    """Canonicalize one post id. Forbid both separators and traversal."""
    name = str(inbound_id or "").strip()
    if not name or not POST_ID_RE.fullmatch(name):
        return ""
    if name in {".", ".."} or ".." in name:
        return ""
    if "/" in name or "\\" in name:
        return ""
    if root:
        root_abs = os.path.abspath(root)
        joined = os.path.abspath(os.path.join(root_abs, "p", name + ".md"))
        p_dir = os.path.abspath(os.path.join(root_abs, "p"))
        if os.path.dirname(joined) != p_dir:
            return ""
        if os.path.basename(joined) != name + ".md":
            return ""
        if os.path.commonpath([p_dir, joined]) != p_dir:
            return ""
    return os.path.join("p", name + ".md")


def parse_post(text):
    raw = str(text or "")
    headers = {}
    body = raw
    if "\n---\n" in raw:
        head, body = raw.split("\n---\n", 1)
    elif raw.startswith("---\n"):
        rest = raw[4:]
        if "\n---\n" in rest:
            head, body = rest.split("\n---\n", 1)
        else:
            head, body = "", raw
    else:
        head = ""
    for line in head.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return {"headers": headers, "body": body, "text": raw}


def is_project_receipt(inbound_id):
    name = str(inbound_id or "").strip()
    if name in PROJECT_NOT_BUYER:
        return True
    return name.startswith("rivet-ship-")


def acceptance_ok(parsed, quote_hash):
    headers = (parsed or {}).get("headers") or {}
    subject = str(headers.get("subject") or "")
    body = str((parsed or {}).get("body") or "")
    hay = (subject + "\n" + body).lower()
    has_accept = (
        "i accept" in hay
        or "buyer yes" in hay
        or ("accept" in hay and SKU_ID in hay)
    )
    digest = str(quote_hash or "").strip().lower()
    has_hash = bool(digest) and digest in hay
    return has_accept and has_hash


def legal_transition(current, wanted):
    current = str(current or "DRAFT").strip().upper() or "DRAFT"
    wanted = str(wanted or current).strip().upper() or current
    if current not in LEGAL_TRANSITIONS:
        current = "DRAFT"
    if wanted == current:
        return current
    if wanted in LEGAL_TRANSITIONS.get(current, frozenset()):
        return wanted
    return current


def request_hash(inbound_id, excerpt_rel, quote_hash):
    payload = "|".join(
        [
            str(inbound_id or "").strip(),
            str(excerpt_rel or "").strip(),
            str(quote_hash or "").strip().lower(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def acceptance_fixture(quote_hash):
    digest = str(quote_hash or "").strip().lower()
    return (
        "from: FIXTURE\n"
        "subject: I ACCEPT sz-paid-validation\n"
        "\n"
        "---\n"
        "\n"
        "BUYER YES\n"
        "quote hash "
        + digest
        + "\n"
    )


def bind_validation_receipt(
    root,
    inbound_id,
    excerpt_rel,
    status="UNKNOWN",
    post_text=None,
    legal_from="DRAFT",
):
    """Bind a STRUCTURAL_ONLY receipt only with buyer acceptance.

    buyer_id is a public inbound id, not a private identity and not
    a project receipt. File existence is not acceptance. PASS is
    refused without buyer evidence on every excerpt, not only GRBN.
    """
    name = str(inbound_id or "").strip()
    rel = inbound_rel(name, root=root)
    excerpt = str(excerpt_rel or "").strip()
    parsed_excerpt = parse_excerpt(_read_bytes(root, excerpt))
    excerpt_ok = bool(parsed_excerpt.get("ok")) and _hex_sha(parsed_excerpt.get("sha256"))
    indexed = source_index(root)
    quote_hash = str(indexed.get("quote_hash") or "")
    row_hash = str(indexed.get("catalog_row_hash") or "")
    inbound_path_ok = bool(rel)
    project = is_project_receipt(name)
    if post_text is None:
        post_text = _read(root, rel) if rel else ""
    parsed_post = parse_post(post_text)
    inbound_exists = bool(rel) and (post_text.strip() != "" if post_text is not None else _exists(root, rel))
    accepted = (
        inbound_path_ok
        and inbound_exists
        and (not project)
        and acceptance_ok(parsed_post, quote_hash)
        and excerpt_ok
        and _hex_sha(quote_hash)
    )
    reason = ""
    legal = "DRAFT"
    if not inbound_path_ok:
        reason = "INVALID_INBOUND_ID"
        legal = "DRAFT"
    elif project:
        reason = "PROJECT_RECEIPT_NOT_BUYER"
        legal = "DRAFT"
    elif not inbound_exists:
        reason = "MISSING_INBOUND"
        legal = "DRAFT"
    elif not acceptance_ok(parsed_post, quote_hash):
        reason = "FILE_IS_NOT_ACCEPTANCE"
        legal = legal_transition(legal_from, "NEEDS_BUYER")
    elif not excerpt_ok:
        reason = "EXCERPT_FINDER_FAILED"
        legal = legal_transition(legal_from, "NEEDS_BUYER")
    elif accepted:
        legal = legal_transition(legal_from, "NEEDS_BUYER")
        legal = legal_transition(legal, "ACCEPTED")
        reason = ""
    wanted = str(status or "UNKNOWN").strip().upper()
    if wanted not in {"PASS", "FAIL", "UNKNOWN"}:
        wanted = "UNKNOWN"
    # PASS would claim CUSTOMER_READY. Refuse it on every excerpt
    # unless the leftover later grows a delivery hash.
    if wanted == "PASS":
        wanted = "UNKNOWN"
    bound = accepted
    req = request_hash(name, excerpt, quote_hash) if inbound_path_ok else ""
    receipt = {
        "kind": "SUBZERO_BUYER_VALIDATION",
        "artifact": excerpt,
        "sha256": str(parsed_excerpt.get("sha256") or ""),
        "status": wanted if bound else "UNKNOWN",
        "legal_state": legal,
        "bound": bound,
        "buyer_id": name if bound else "",
        "quote_hash": quote_hash,
        "catalog_row_hash": row_hash,
        "request_hash": req,
        "delivery_hash": "",
        "source_commit": AUDITED_COMMIT,
        "source_tree": AUDITED_TREE,
        "bind_reason": reason,
        "no_auth": True,
        "no_gate": True,
        "login_required": False,
        "privileged_tier": False,
    }
    return {
        "receipt": receipt,
        "inbound_ok": inbound_path_ok and inbound_exists and (not project),
        "inbound_path_ok": inbound_path_ok,
        "excerpt_ok": excerpt_ok,
        "header": parsed_excerpt,
        "binding_state": "BUYER_BOUND" if bound else "UNBOUND",
        "legal_state": legal,
        "bind_reason": reason,
        "evidence_class": "STRUCTURAL_ONLY" if excerpt_ok else "UNKNOWN",
        "cash_state": "NOT_LANDED",
        "demand": "UNKNOWN",
    }


def receipt_schema_ok(receipt):
    """Match the already-landed buyer_receipt required fields plus hashes."""
    receipt = receipt or {}
    if str(receipt.get("kind") or "") != "SUBZERO_BUYER_VALIDATION":
        return False
    if not str(receipt.get("artifact") or "").strip():
        return False
    if receipt.get("bound") is True and not _hex_sha(receipt.get("sha256")):
        return False
    if receipt.get("status") not in {"PASS", "FAIL", "UNKNOWN"}:
        return False
    if receipt.get("legal_state") not in {"DRAFT", "NEEDS_BUYER", "ACCEPTED", "DELIVERED"}:
        return False
    if receipt.get("bound") is True and not str(receipt.get("buyer_id") or "").strip():
        return False
    if receipt.get("bound") is True and is_project_receipt(receipt.get("buyer_id")):
        return False
    if receipt.get("bound") is True and not _hex_sha(receipt.get("quote_hash")):
        return False
    if receipt.get("bound") is True and not _hex_sha(receipt.get("request_hash")):
        return False
    if receipt.get("bound") is not True and receipt.get("bound") is not False:
        return False
    if str(receipt.get("source_tree") or "") != AUDITED_TREE:
        return False
    return (
        receipt.get("no_auth") is True
        and receipt.get("no_gate") is True
        and receipt.get("login_required") is False
        and receipt.get("privileged_tier") is False
    )


def classify_binding(row):
    """Name the live bind. Invented buyers / cash / runtime fail."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "H-008 receipt leftover not read. Absence was not stillness. "
                "FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("finder") or "").strip().lower() in {"failed", "unknown", "error"}:
        return {
            "state": "FINDER-FAILED",
            "note": (
                "finder/tool call failed on "
                + SKU_ID
                + " bind. UNKNOWN, never 0."
            ),
        }
    unresolved = [
        name
        for name in (
            "quote_price_state",
            "collected_cash_state",
            "structural_only_state",
            "runtime_measured_state",
            "customer_ready_state",
        )
        if str(row.get(name) or "").strip().upper() == "UNRESOLVED"
    ]
    if unresolved:
        return {
            "state": "FINDER-FAILED",
            "note": (
                "missing numeric field(s) stayed UNRESOLVED: "
                + ", ".join(unresolved)
                + ". Coercion to 0 is forbidden. FINDER-FAILED, never 0."
            ),
        }
    cash = row.get("collected_cash_usd")
    if bool(row.get("claims_cash")) or (cash not in (None, 0) and cash != 0):
        return {
            "state": "NOT_LANDED",
            "note": (
                "A buyer-bound receipt is not cash proof. Collected cash stays "
                "$0 / NOT_LANDED. FINDER-FAILED, never 0."
            ),
        }
    if bool(row.get("claims_runtime")) or bool(row.get("runtime_proof")):
        return {
            "state": "NOT_LANDED",
            "note": (
                "A buyer-bound receipt is not runtime proof. "
                "FINDER-FAILED, never 0."
            ),
        }
    if bool(row.get("claims_demand")) or str(row.get("demand") or "").strip().upper() not in {
        "",
        "UNKNOWN",
    }:
        return {
            "state": "NOT_LANDED",
            "note": (
                "A bind implementation is not demand proof. Demand stays "
                "UNKNOWN. FINDER-FAILED, never 0."
            ),
        }
    if int(row.get("live_bound_receipts") or 0) > 0:
        return {
            "state": "NOT_LANDED",
            "note": (
                "Live tree invented a buyer-bound receipt. Demand stays "
                "UNKNOWN. FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("binding_state") or "").strip().upper() != "UNBOUND":
        return {
            "state": "NOT_LANDED",
            "note": (
                "Live binding_state must stay UNBOUND until a public inbound "
                "names a file. FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("legal_state") or "DRAFT").strip().upper() not in {"DRAFT", "NEEDS_BUYER"}:
        return {
            "state": "NOT_LANDED",
            "note": (
                "Live legal_state must stay DRAFT or NEEDS_BUYER. "
                "ACCEPTED/DELIVERED without a buyer is an overclaim. "
                "FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("sku_id") or "").strip() != SKU_ID:
        return {
            "state": "NOT_LANDED",
            "note": (
                "source-index sku is "
                + (str(row.get("sku_id") or "missing"))
                + ", not "
                + SKU_ID
                + ". FINDER-FAILED, never 0."
            ),
        }
    if row.get("quote_price") != QUOTE_PRICE:
        return {
            "state": "NOT_LANDED",
            "note": (
                SKU_ID
                + " price is "
                + str(row.get("quote_price"))
                + ", not "
                + str(QUOTE_PRICE)
                + ". FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("p01_id") or "").strip() != P01_ID:
        return {
            "state": "NOT_LANDED",
            "note": "P01_catalog_receipt FINDER-FAILED, never 0.",
        }
    if not row.get("schema_has_buyer"):
        return {
            "state": "NOT_LANDED",
            "note": "buyer_receipt schema FINDER-FAILED, never 0.",
        }
    if not row.get("bind_works"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "quote-draft → buyer-bound bind did not implement. "
                "FINDER-FAILED, never 0."
            ),
        }
    return {
        "state": "UNBOUND",
        "note": (
            SKU_ID
            + " / "
            + P01_ID
            + " quote-draft → buyer-bound receipt is implemented. "
            "Live bind stays UNBOUND. Not runtime, not demand, not cash."
        ),
    }


def measure_from_rows(facts):
    """Classify measured file/phrase facts. Missing calibration is UNMEASURED."""
    facts = facts or {}
    return {
        "measured": True,
        "card_present": bool(facts.get("card_present")),
        "catalog_present": bool(facts.get("catalog_present")),
        "door_present": bool(facts.get("door_present")),
        "quote_present": bool(facts.get("quote_present")),
        "arch_present": bool(facts.get("arch_present")),
        "buyers_present": bool(facts.get("buyers_present")),
        "schema_present": bool(facts.get("schema_present")),
        "landed_present": list(facts.get("landed_present") or []),
        "landed_missing": list(facts.get("landed_missing") or []),
        "found_phrases": list(facts.get("found_phrases") or []),
        "sku_id": str(facts.get("sku_id") or ""),
        "quote_class": str(facts.get("quote_class") or ""),
        "quote_price": facts.get("quote_price"),
        "quote_price_state": str(facts.get("quote_price_state") or "UNRESOLVED"),
        "quote_hash": str(facts.get("quote_hash") or ""),
        "catalog_row_hash": str(facts.get("catalog_row_hash") or ""),
        "p01_id": str(facts.get("p01_id") or ""),
        "arch_status": str(facts.get("arch_status") or ""),
        "arch_implements": str(facts.get("arch_implements") or ""),
        "schema_has_buyer": bool(facts.get("schema_has_buyer")),
        "schema_no_auth": bool(facts.get("schema_no_auth")),
        "schema_no_gate": bool(facts.get("schema_no_gate")),
        "binding_state": str(facts.get("binding_state") or ""),
        "legal_state": str(facts.get("legal_state") or "DRAFT"),
        "live_bound_receipts": int(facts.get("live_bound_receipts") or 0),
        "bind_works": bool(facts.get("bind_works")),
        "grbn_sha": str(facts.get("grbn_sha") or ""),
        "collected_cash_usd": facts.get("collected_cash_usd"),
        "collected_cash_state": str(facts.get("collected_cash_state") or "UNRESOLVED"),
        "cash_state": str(facts.get("cash_state") or ""),
        "demand": str(facts.get("demand") or ""),
        "runtime_proof": bool(facts.get("runtime_proof")),
        "structural_only": facts.get("structural_only"),
        "structural_only_state": str(facts.get("structural_only_state") or "UNRESOLVED"),
        "runtime_measured": facts.get("runtime_measured"),
        "runtime_measured_state": str(facts.get("runtime_measured_state") or "UNRESOLVED"),
        "customer_ready": facts.get("customer_ready"),
        "customer_ready_state": str(facts.get("customer_ready_state") or "UNRESOLVED"),
        "claims_cash": bool(facts.get("claims_cash")),
        "claims_runtime": bool(facts.get("claims_runtime")),
        "claims_demand": bool(facts.get("claims_demand")),
        "posting_open": bool(facts.get("posting_open")),
        "no_auth": bool(facts.get("no_auth")),
        "no_gate": bool(facts.get("no_gate")),
        "calibration_ok": bool(facts.get("calibration_ok")),
        "calibration_hits": list(facts.get("calibration_hits") or []),
        "search_space": list(facts.get("search_space") or SEARCH_SPACE),
        "misses": list(facts.get("misses") or []),
        "audited_commit": str(facts.get("audited_commit") or AUDITED_COMMIT),
        "audited_tree": str(facts.get("audited_tree") or AUDITED_TREE),
    }


def classify(row):
    """Turn a measured receipt census into a desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "SUBZERO receipt leftover not read. Absence was not stillness. "
                "A Slack H-008 / H-009 body is not the file. FINDER-FAILED, never 0."
            ),
        }
    if row.get("calibration_ok") is False:
        return {
            "state": "UNMEASURED",
            "note": (
                "known-present calibration failed: "
                + ", ".join(row.get("calibration_hits") or [])
                + ". Search-zero testing is instrument failure, not absence proof. "
                "FINDER-FAILED, never 0."
            ),
        }
    misses = list(row.get("misses") or [])
    landed_missing = list(row.get("landed_missing") or [])
    if (
        not row.get("card_present")
        or not row.get("catalog_present")
        or not row.get("door_present")
        or not row.get("quote_present")
        or not row.get("arch_present")
        or not row.get("buyers_present")
        or not row.get("schema_present")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "missing leftover path(s): "
                + ", ".join(misses or ["card/catalog/door/source-index"])
                + ". JOJO H-009 / #2329 second-pass / binder-not-buyer-bound "
                "talk is CLAIMED until the leftover ships. "
                "FINDER-FAILED, never 0."
            ),
        }
    if landed_missing:
        return {
            "state": "NOT_LANDED",
            "note": (
                "named already-landed leftover(s) missing: "
                + ", ".join(landed_missing)
                + ". Census is incomplete. FINDER-FAILED, never 0."
            ),
        }
    binding = classify_binding(row)
    if binding["state"] != "UNBOUND":
        return {
            "state": "NOT_LANDED",
            "note": binding["note"],
        }
    needed = [
        phrase
        for phrase in REQUIRED_PHRASES
        if phrase not in (row.get("found_phrases") or [])
    ]
    if needed or not row.get("posting_open") or not row.get("no_auth") or not row.get("no_gate"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "leftover present but incomplete. Missing phrases: "
                + ", ".join(needed)
                + ". Open door + no auth + no gate required. Talk is CLAIMED. "
                "FINDER-FAILED, never 0."
            ),
        }
    return {
        "state": "INTEGRATED",
        "note": (
            "SUBZERO receipt leftover is on this tree. "
            + SKU_ID
            + " / "
            + P01_ID
            + " quote-draft → buyer-bound bind is implemented. "
            "Live bind stays UNBOUND. File existence is not a buyer. "
            "Not runtime, not demand, not cash. "
            "A Slack H-008 / H-009 body is still not the file."
        ),
    }


def _bind_proofs(root):
    """Prove refusals and a synthetic acceptance bind. Not demand."""
    slash = bind_validation_receipt(root, "..\\ground\\EXECUTE", GRBN_REL)
    slash_fwd = bind_validation_receipt(root, "../ground/EXECUTE", GRBN_REL)
    quote_as_buyer = bind_validation_receipt(root, QUOTE_RECEIPT, GRBN_REL)
    missing = bind_validation_receipt(
        root, "fixture-h008-inbound-20260825-01", GRBN_REL
    )
    pass_grbn = bind_validation_receipt(root, QUOTE_RECEIPT, GRBN_REL, status="PASS")
    pass_hdvs = bind_validation_receipt(root, QUOTE_RECEIPT, HDVS_REL, status="PASS")
    quote_hash = file_sha(root, DEFAULT_QUOTE)
    fixture = bind_validation_receipt(
        root,
        "fixture-buyer-accept-20260825-01",
        GRBN_REL,
        status="PASS",
        post_text=acceptance_fixture(quote_hash),
    )
    return {
        "slash": slash,
        "slash_fwd": slash_fwd,
        "quote_as_buyer": quote_as_buyer,
        "missing": missing,
        "pass_grbn": pass_grbn,
        "pass_hdvs": pass_hdvs,
        "fixture": fixture,
        "ok": (
            slash["binding_state"] == "UNBOUND"
            and slash["inbound_path_ok"] is False
            and slash["bind_reason"] == "INVALID_INBOUND_ID"
            and slash_fwd["binding_state"] == "UNBOUND"
            and quote_as_buyer["binding_state"] == "UNBOUND"
            and quote_as_buyer["bind_reason"] == "PROJECT_RECEIPT_NOT_BUYER"
            and quote_as_buyer["receipt"]["buyer_id"] == ""
            and missing["binding_state"] == "UNBOUND"
            and missing["excerpt_ok"]
            and str((missing.get("header") or {}).get("sha256") or "") == GRBN_SHA
            and pass_grbn["receipt"]["status"] == "UNKNOWN"
            and pass_hdvs["receipt"]["status"] == "UNKNOWN"
            and fixture["binding_state"] == "BUYER_BOUND"
            and fixture["legal_state"] == "ACCEPTED"
            and fixture["receipt"]["status"] == "UNKNOWN"
            and fixture["receipt"]["buyer_id"] == "fixture-buyer-accept-20260825-01"
            and receipt_schema_ok(fixture["receipt"])
            and fixture["evidence_class"] == "STRUCTURAL_ONLY"
            and str(fixture["receipt"].get("sha256") or "") == GRBN_SHA
            and str(fixture["receipt"].get("source_tree") or "") == AUDITED_TREE
        ),
    }


def measure_root(root):
    root = os.path.abspath(root)
    misses = []
    blobs = []
    for rel in SEARCH_SPACE:
        text = _read(root, rel)
        if not text:
            misses.append(rel)
        else:
            blobs.append(text)
    hay = "\n".join(blobs).lower()
    found = [phrase for phrase in REQUIRED_PHRASES if phrase in hay]
    landed_present = [rel for rel in ALREADY_LANDED if _exists(root, rel)]
    landed_missing = [rel for rel in ALREADY_LANDED if not _exists(root, rel)]
    catalog = load_json(_read(root, DEFAULT_CATALOG), "catalog")
    indexed = source_index(root)
    calibration_hits = [rel for rel in CALIBRATION if _exists(root, rel)]
    calibration_ok = len(calibration_hits) == len(CALIBRATION)
    if not calibration_ok:
        for rel in CALIBRATION:
            if rel not in calibration_hits and rel not in misses:
                misses.append("calibration:" + rel)
    posting_open = (
        str(catalog.get("posting") or "") == "OPEN"
        and "open door" in hay
        and "unseated" in hay
    )
    proofs = _bind_proofs(root)
    live_bound = catalog.get("live_bound_receipts")
    live_bound_n = present_int({"live_bound_receipts": live_bound}, "live_bound_receipts")
    facts = {
        "card_present": _exists(root, DEFAULT_CARD),
        "catalog_present": _exists(root, DEFAULT_CATALOG) and not catalog.get("error"),
        "door_present": _exists(root, DEFAULT_DOOR),
        "quote_present": _exists(root, DEFAULT_QUOTE) and not indexed.get("quote_error"),
        "arch_present": _exists(root, DEFAULT_ARCH) and not indexed.get("arch_error"),
        "buyers_present": _exists(root, DEFAULT_BUYERS) and not indexed.get("buyers_error"),
        "schema_present": _exists(root, DEFAULT_SCHEMA)
        and not indexed.get("schema_error")
        and indexed.get("schema_has_buyer"),
        "landed_present": landed_present,
        "landed_missing": landed_missing,
        "found_phrases": found,
        "sku_id": indexed.get("sku_id") or "",
        "quote_class": indexed.get("quote_class") or "",
        "quote_price": indexed.get("quote_price"),
        "quote_price_state": indexed.get("quote_price_state") or "UNRESOLVED",
        "quote_hash": indexed.get("quote_hash") or "",
        "catalog_row_hash": indexed.get("catalog_row_hash") or "",
        "p01_id": indexed.get("p01_id") or "",
        "arch_status": indexed.get("arch_status") or "",
        "arch_implements": indexed.get("arch_implements") or "",
        "schema_has_buyer": bool(indexed.get("schema_has_buyer")),
        "schema_no_auth": bool(indexed.get("schema_no_auth")),
        "schema_no_gate": bool(indexed.get("schema_no_gate")),
        "binding_state": str(catalog.get("binding_state") or "UNBOUND").upper(),
        "legal_state": str(catalog.get("legal_state") or "DRAFT").upper(),
        "live_bound_receipts": live_bound_n if live_bound_n is not None else 0,
        "bind_works": proofs["ok"],
        "grbn_sha": str((proofs["missing"].get("header") or {}).get("sha256") or ""),
        "collected_cash_usd": indexed.get("collected_cash_usd"),
        "collected_cash_state": indexed.get("collected_cash_state") or "UNRESOLVED",
        "cash_state": indexed.get("cash_state") or "",
        "demand": indexed.get("demand") or "",
        "runtime_proof": bool(indexed.get("runtime_proof")),
        "structural_only": indexed.get("structural_only"),
        "structural_only_state": indexed.get("structural_only_state") or "UNRESOLVED",
        "runtime_measured": indexed.get("runtime_measured"),
        "runtime_measured_state": indexed.get("runtime_measured_state") or "UNRESOLVED",
        "customer_ready": indexed.get("customer_ready"),
        "customer_ready_state": indexed.get("customer_ready_state") or "UNRESOLVED",
        "claims_cash": bool(catalog.get("claims_cash")),
        "claims_runtime": bool(catalog.get("claims_runtime")),
        "claims_demand": bool(catalog.get("claims_demand")),
        "posting_open": posting_open,
        "no_auth": bool(catalog.get("no_auth")) and "no auth" in hay,
        "no_gate": bool(catalog.get("no_gate")) and "no gate" in hay,
        "calibration_ok": calibration_ok,
        "calibration_hits": calibration_hits,
        "search_space": list(SEARCH_SPACE),
        "misses": misses,
        "audited_commit": str(catalog.get("audited_commit") or AUDITED_COMMIT),
        "audited_tree": str(catalog.get("audited_tree") or AUDITED_TREE),
        "slack_ts": str(catalog.get("slack_ts") or SLACK_TS),
    }
    binding = classify_binding(measure_from_rows(facts))
    row = measure_from_rows(facts)
    row.update(
        {
            "slack_ts": facts["slack_ts"],
            "audit_slack_ts": AUDIT_SLACK_TS,
            "cell": CELL,
            "audit_cell": AUDIT_CELL,
            "x": [rel for rel in SEARCH_SPACE if _exists(root, rel)],
            "y": {
                "calibration_hits": calibration_hits,
                "found_phrases": found,
                "landed_present": landed_present,
                "sku_id": facts["sku_id"],
                "quote_price": facts["quote_price"],
                "quote_price_state": facts["quote_price_state"],
                "p01_id": facts["p01_id"],
                "binding_state": facts["binding_state"],
                "legal_state": facts["legal_state"],
                "bind_works": facts["bind_works"],
                "live_bound_receipts": facts["live_bound_receipts"],
                "quote_receipt": QUOTE_RECEIPT,
                "audited_tree": facts["audited_tree"],
            },
            "z": (
                "misses "
                + json.dumps(misses + landed_missing)
                + " / FINDER-FAILED never 0 / bind "
                + binding["state"]
            ),
        }
    )
    return row


def self_test():
    empty = classify({})
    assert empty["state"] == "UNMEASURED", empty
    missing = classify(
        measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "misses": ["ground/SUBZERO_RECEIPT.md"],
                "calibration_ok": True,
            }
        )
    )
    assert missing["state"] == "NOT_LANDED", missing
    cash = classify_binding(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "quote_price": QUOTE_PRICE,
            "quote_price_state": "PRESENT",
            "collected_cash_state": "PRESENT",
            "collected_cash_usd": 0,
            "structural_only_state": "PRESENT",
            "runtime_measured_state": "PRESENT",
            "customer_ready_state": "PRESENT",
            "p01_id": P01_ID,
            "schema_has_buyer": True,
            "bind_works": True,
            "binding_state": "UNBOUND",
            "legal_state": "DRAFT",
            "claims_cash": True,
        }
    )
    assert cash["state"] == "NOT_LANDED", cash
    unresolved = classify_binding(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "quote_price": None,
            "quote_price_state": "UNRESOLVED",
            "collected_cash_state": "PRESENT",
            "structural_only_state": "PRESENT",
            "runtime_measured_state": "PRESENT",
            "customer_ready_state": "PRESENT",
            "p01_id": P01_ID,
            "schema_has_buyer": True,
            "bind_works": True,
            "binding_state": "UNBOUND",
            "legal_state": "DRAFT",
        }
    )
    assert unresolved["state"] == "FINDER-FAILED", unresolved
    invented = classify_binding(
        {
            "measured": True,
            "sku_id": SKU_ID,
            "quote_price": QUOTE_PRICE,
            "quote_price_state": "PRESENT",
            "collected_cash_state": "PRESENT",
            "collected_cash_usd": 0,
            "structural_only_state": "PRESENT",
            "runtime_measured_state": "PRESENT",
            "customer_ready_state": "PRESENT",
            "p01_id": P01_ID,
            "schema_has_buyer": True,
            "bind_works": True,
            "binding_state": "UNBOUND",
            "legal_state": "DRAFT",
            "live_bound_receipts": 1,
            "demand": "UNKNOWN",
        }
    )
    assert invented["state"] == "NOT_LANDED", invented
    return "ok"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure SUBZERO receipt leftover")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        print(self_test())
        return 0
    row = measure_root(args.root)
    verdict = classify(row)
    payload = {"verdict": verdict, "row": row}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if verdict["state"] == "INTEGRATED" else 1


if __name__ == "__main__":
    sys.exit(main())
