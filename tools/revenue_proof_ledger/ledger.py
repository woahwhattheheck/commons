#!/usr/bin/env python3
"""Reduce immutable revenue receipts into a fail-closed proof ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

INPUT_SCHEMA = "commons-revenue-proof-input/v1"
OUTPUT_SCHEMA = "commons-revenue-proof-ledger/v1"
AUTH = {"unknown": 0, "partial": 1, "complete": 2}
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
CURRENCY = re.compile(r"[A-Z][A-Z0-9]{2,7}\Z")
AMOUNT = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,18})?\Z")
IDENT = re.compile(r"[^\s]{1,300}\Z")
COMMON = {"kind", "opportunity_id", "source", "authority", "evidence_digest"}
FIELDS = {
    "opportunity": {"currency", "expected_amount", "identity_status"},
    "lookup": {"scope"},
    "delivery": {"delivery_id", "state", "current", "currency", "earned_amount", "credit"},
    "settlement": {"delivery_id", "settlement_id", "movement", "state", "currency", "amount"},
}


class InputError(ValueError):
    pass


def _obj(v: Any, w: str) -> dict[str, Any]:
    if not isinstance(v, dict):
        raise InputError(f"{w} must be an object")
    return v


def _id(v: Any, w: str) -> str:
    if not isinstance(v, str) or not IDENT.fullmatch(v):
        raise InputError(f"{w} must be a non-whitespace identifier")
    return v


def _enum(v: Any, allowed: set[str] | dict[str, int], w: str) -> str:
    if v not in allowed:
        raise InputError(f"{w} is unsupported")
    return v


def _digest(v: Any, w: str) -> str:
    if not isinstance(v, str) or not DIGEST.fullmatch(v):
        raise InputError(f"{w} must be lowercase sha256:<64 hex>")
    return v


def _currency(v: Any, w: str) -> str:
    if not isinstance(v, str) or not CURRENCY.fullmatch(v):
        raise InputError(f"{w} must be an uppercase currency code")
    return v


def _amount(v: Any, w: str, *, positive: bool = False) -> Decimal:
    if not isinstance(v, str) or not AMOUNT.fullmatch(v):
        raise InputError(f"{w} must be a plain non-negative decimal string")
    try:
        d = Decimal(v)
    except InvalidOperation as exc:
        raise InputError(f"{w} is not a decimal") from exc
    if not d.is_finite() or d < 0 or (positive and d == 0):
        raise InputError(f"{w} has invalid value")
    return d


def _fmt(d: Decimal) -> str:
    if d == 0:
        return "0"
    s = format(d.normalize(), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _amin(values: Iterable[str]) -> str:
    rows = list(values)
    return min(rows, key=lambda x: AUTH[x]) if rows else "unknown"


def _credit(v: Any, w: str) -> dict[str, set[str]]:
    raw = {} if v is None else _obj(v, w)
    keys = {"source_authors", "reviewers", "mergers"}
    extra = sorted(set(raw) - keys)
    if extra:
        raise InputError(f"{w} has unknown fields: {', '.join(extra)}")
    out = {}
    for key in keys:
        rows = raw.get(key, [])
        if not isinstance(rows, list) or any(not isinstance(x, str) or not x.strip() for x in rows):
            raise InputError(f"{w}.{key} must be an array of non-empty strings")
        out[key] = set(rows)
    return out


def _base(opp_id: str) -> dict[str, Any]:
    return {
        "id": opp_id,
        "currency": None,
        "expected": None,
        "evidence": set(),
        "auth": [],
        "issues": set(),
    }


def reduce_ledger(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _obj(payload, "input")
    if payload.get("schema") != INPUT_SCHEMA:
        raise InputError(f"schema must be {INPUT_SCHEMA}")
    receipts = payload.get("receipts")
    if not isinstance(receipts, list):
        raise InputError("receipts must be an array")

    opps: dict[str, dict[str, Any]] = {}
    deliveries: dict[str, dict[str, Any]] = {}
    settlements: dict[str, dict[str, Any]] = {}
    lookups: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    lookup_evidence: dict[str, set[str]] = defaultdict(set)

    for i, raw in enumerate(receipts):
        r = _obj(raw, f"receipts[{i}]")
        kind = r.get("kind")
        if kind not in FIELDS:
            raise InputError(f"receipts[{i}].kind is unsupported")
        extra = sorted(set(r) - (COMMON | FIELDS[kind]))
        if extra:
            raise InputError(f"receipts[{i}] has unknown fields: {', '.join(extra)}")
        w = f"receipts[{i}]"
        oid = _id(r.get("opportunity_id"), f"{w}.opportunity_id")
        _id(r.get("source"), f"{w}.source")
        authority = _enum(r.get("authority"), AUTH, f"{w}.authority")
        digest = _digest(r.get("evidence_digest"), f"{w}.evidence_digest")
        opp = opps.setdefault(oid, _base(oid))
        opp["evidence"].add(digest)
        opp["auth"].append(authority)

        if kind == "opportunity":
            identity = _enum(r.get("identity_status"), {"canonical", "ambiguous"}, f"{w}.identity_status")
            if identity == "ambiguous":
                opp["issues"].add("opportunity_identity_ambiguous")
            currency = _currency(r.get("currency"), f"{w}.currency")
            expected = _amount(r.get("expected_amount"), f"{w}.expected_amount")
            if opp["currency"] is None:
                opp["currency"], opp["expected"] = currency, expected
            elif opp["currency"] != currency:
                opp["issues"].add("opportunity_currency_mismatch")
            elif opp["expected"] != expected:
                opp["issues"].add("opportunity_amount_mismatch")
            continue

        if kind == "lookup":
            scope = _enum(r.get("scope"), {"delivery", "settlement"}, f"{w}.scope")
            lookups[oid][scope].append(authority)
            lookup_evidence[oid].add(digest)
            continue

        if kind == "delivery":
            did = _id(r.get("delivery_id"), f"{w}.delivery_id")
            state = _enum(r.get("state"), {"delivered", "accepted", "rejected", "superseded"}, f"{w}.state")
            current = r.get("current")
            if type(current) is not bool:
                raise InputError(f"{w}.current must be a JSON boolean")
            currency = _currency(r.get("currency"), f"{w}.currency")
            earned_raw = r.get("earned_amount")
            earned = _amount(earned_raw, f"{w}.earned_amount", positive=True) if state == "accepted" else Decimal(0)
            if state != "accepted" and earned_raw is not None and _amount(earned_raw, f"{w}.earned_amount") != 0:
                opp["issues"].add(f"nonaccepted_delivery_has_earned_amount:{did}")
            credits = _credit(r.get("credit"), f"{w}.credit")
            semantic = (oid, state, current, currency, earned)
            prev = deliveries.get(did)
            if prev is None:
                deliveries[did] = {
                    "id": did, "oid": oid, "state": state, "current": current,
                    "currency": currency, "earned": earned, "semantic": semantic,
                    "evidence": {digest}, "auth": [authority], **credits,
                }
            elif prev["semantic"] != semantic:
                opp["issues"].add(f"delivery_identity_conflict:{did}")
                prev["evidence"].add(digest); prev["auth"].append(authority)
            else:
                prev["evidence"].add(digest); prev["auth"].append(authority)
                for key in ("source_authors", "reviewers", "mergers"):
                    prev[key].update(credits[key])
            continue

        sid = _id(r.get("settlement_id"), f"{w}.settlement_id")
        did = _id(r.get("delivery_id"), f"{w}.delivery_id")
        movement = _enum(r.get("movement"), {"payment", "refund", "reversal", "dispute"}, f"{w}.movement")
        state = _enum(r.get("state"), {"settled", "pending", "failed"}, f"{w}.state")
        currency = _currency(r.get("currency"), f"{w}.currency")
        amount = _amount(r.get("amount"), f"{w}.amount", positive=True)
        semantic = (oid, did, movement, state, currency, amount)
        prev = settlements.get(sid)
        if prev is None:
            settlements[sid] = {
                "id": sid, "oid": oid, "did": did, "movement": movement,
                "state": state, "currency": currency, "amount": amount,
                "semantic": semantic, "evidence": {digest}, "auth": [authority],
            }
        elif prev["semantic"] != semantic:
            for affected in {prev["oid"], oid}:
                opps.setdefault(affected, _base(affected))["issues"].add(f"settlement_id_reused:{sid}")
            prev["evidence"].add(digest); prev["auth"].append(authority)
        else:
            prev["evidence"].add(digest); prev["auth"].append(authority)

    d_by_opp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in deliveries.values():
        d_by_opp[d["oid"]].append(d)
        opp = opps.setdefault(d["oid"], _base(d["oid"]))
        opp["evidence"].update(d["evidence"]); opp["auth"].extend(d["auth"])
    s_by_opp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in settlements.values():
        s_by_opp[s["oid"]].append(s)
        opp = opps.setdefault(s["oid"], _base(s["oid"]))
        opp["evidence"].update(s["evidence"]); opp["auth"].extend(s["auth"])

    rows = []
    totals: dict[str, dict[str, Decimal]] = defaultdict(lambda: {
        "pipeline_expected": Decimal(0), "earned_unsettled": Decimal(0),
        "cash_settled": Decimal(0), "reversed_or_disputed": Decimal(0),
    })
    for oid in sorted(opps):
        opp = opps[oid]
        issues = set(opp["issues"])
        evidence = set(opp["evidence"]) | lookup_evidence[oid]
        currency = opp["currency"]
        expected = opp["expected"] or Decimal(0)
        if "opportunity_currency_mismatch" in issues:
            currency = "UNKNOWN"
        if "opportunity_amount_mismatch" in issues:
            expected = Decimal(0)
        if currency is None or opp["expected"] is None:
            issues.add("canonical_opportunity_terms_missing"); currency = currency or "UNKNOWN"

        delivery_lookup = _amin(lookups[oid]["delivery"])
        settlement_lookup = _amin(lookups[oid]["settlement"])
        if not lookups[oid]["delivery"]: issues.add("delivery_lookup_missing")
        if not lookups[oid]["settlement"]: issues.add("settlement_lookup_missing")

        ds = sorted(d_by_opp.get(oid, []), key=lambda x: x["id"])
        active = [d for d in ds if d["state"] == "accepted" and d["current"]]
        if len(active) > 1: issues.add("ambiguous_current_accepted_delivery")
        current = active[0] if len(active) == 1 else None
        earned = current["earned"] if current else Decimal(0)
        credit = {"source_authors": set(), "reviewers": set(), "mergers": set()}
        for d in ds:
            evidence.update(d["evidence"])
            for key in credit: credit[key].update(d[key])
            if currency != "UNKNOWN" and d["currency"] != currency:
                issues.add(f"delivery_currency_mismatch:{d['id']}")
        if current and expected and earned > expected:
            issues.add("earned_amount_exceeds_pipeline_expected")

        gross = Decimal(0); reversed_amt = Decimal(0); settlement_ids = []
        for s in sorted(s_by_opp.get(oid, []), key=lambda x: x["id"]):
            evidence.update(s["evidence"]); settlement_ids.append(s["id"])
            if currency != "UNKNOWN" and s["currency"] != currency:
                issues.add(f"settlement_currency_mismatch:{s['id']}")
            d = deliveries.get(s["did"])
            if d is None or d["oid"] != oid:
                issues.add(f"settlement_delivery_missing:{s['id']}")
            elif current is None or d["id"] != current["id"]:
                issues.add(f"settlement_on_noncurrent_delivery:{s['id']}")
            if s["state"] == "settled":
                if s["movement"] == "payment": gross += s["amount"]
                else: reversed_amt += s["amount"]
        observed = gross - reversed_amt
        if observed < 0: issues.add("reversals_exceed_settled_payments")
        if earned and observed > earned: issues.add("settled_cash_exceeds_earned_amount")
        raw_auth = _amin([*opp["auth"], delivery_lookup, settlement_lookup])
        authority = "unknown" if issues else raw_auth
        cash = max(observed, Decimal(0)) if authority == "complete" and current else Decimal(0)
        unsettled = max(earned - cash, Decimal(0))
        row = {
            "opportunity_id": oid, "delivery_id": current["id"] if current else None,
            "currency": currency, "pipeline_expected": _fmt(expected),
            "earned_unsettled": _fmt(unsettled), "cash_settled": _fmt(cash),
            "reversed_or_disputed": _fmt(reversed_amt),
            "observed_settled_payments": _fmt(gross), "observed_net_cash": _fmt(observed),
            "authority": authority,
            "lookup_authority": {"delivery": delivery_lookup, "settlement": settlement_lookup},
            "issues": sorted(issues), "evidence_digests": sorted(evidence),
            "settlement_ids": settlement_ids,
            "credit_lineage": {key: sorted(value) for key, value in credit.items()},
        }
        rows.append(row)
        if currency != "UNKNOWN":
            bucket = totals[currency]
            bucket["pipeline_expected"] += expected; bucket["earned_unsettled"] += unsettled
            bucket["cash_settled"] += cash; bucket["reversed_or_disputed"] += reversed_amt

    output: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "authority": _amin(row["authority"] for row in rows),
        "currency_totals": {
            cur: {k: _fmt(v) for k, v in sorted(bucket.items())}
            for cur, bucket in sorted(totals.items())
        },
        "opportunities": rows,
        "issues": sorted({issue for row in rows for issue in row["issues"]}),
    }
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    output["ledger_digest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return output


def render_summary(ledger: dict[str, Any]) -> str:
    if ledger.get("schema") != OUTPUT_SCHEMA:
        raise InputError(f"ledger schema must be {OUTPUT_SCHEMA}")
    lines = [
        "# Revenue proof ledger", "", f"Authority: **{ledger['authority']}**  ",
        f"Ledger digest: `{ledger['ledger_digest']}`", "",
        "| Opportunity | Delivery | Currency | Pipeline expected | Earned unsettled | Cash settled | Reversed/disputed | Authority |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in ledger["opportunities"]:
        delivery = row["delivery_id"] or "—"
        lines.append(
            f"| {row['opportunity_id']} | {delivery} | {row['currency']} | {row['pipeline_expected']} | "
            f"{row['earned_unsettled']} | {row['cash_settled']} | {row['reversed_or_disputed']} | {row['authority']} |"
        )
        if row["issues"]:
            lines.append(f"\nIssues for `{row['opportunity_id']}`: " + ", ".join(f"`{x}`" for x in row["issues"]))
    lines += ["", "## Currency totals", ""]
    for cur, b in sorted(ledger["currency_totals"].items()):
        lines.append(
            f"- **{cur}** — pipeline {b['pipeline_expected']}; earned unsettled {b['earned_unsettled']}; "
            f"cash settled {b['cash_settled']}; reversed/disputed {b['reversed_or_disputed']}"
        )
    return "\n".join(lines).rstrip() + "\n"


def _read(path: Path) -> dict[str, Any]:
    try: raw = path.read_bytes()
    except OSError as exc: raise InputError(f"cannot read input: {exc}") from exc
    if len(raw) > 16 * 1024 * 1024: raise InputError("input exceeds 16 MiB")
    try:
        return _obj(json.loads(raw.decode("utf-8", "strict"), parse_constant=lambda x: (_ for _ in ()).throw(InputError(f"non-standard JSON constant: {x}"))), "input")
    except UnicodeDecodeError as exc: raise InputError("input is not valid UTF-8") from exc
    except json.JSONDecodeError as exc: raise InputError(f"invalid JSON: {exc}") from exc


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        data = memoryview(text.encode())
        while data:
            n = os.write(fd, data)
            if n <= 0: raise OSError("short write")
            data = data[n:]
        os.fsync(fd)
    finally: os.close(fd)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path); p.add_argument("--json-out", type=Path, required=True); p.add_argument("--summary-out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        ledger = reduce_ledger(_read(a.input))
        _write(a.json_out, json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        _write(a.summary_out, render_summary(ledger))
    except (InputError, OSError) as exc:
        p.exit(2, f"revenue_proof_ledger: {exc}\n")
    return 0 if ledger["authority"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
