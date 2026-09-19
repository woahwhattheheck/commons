"""Bind an existing milestone assembler's synthetic example to proposed terms.

Reads OP5-MARROW's published engagement.json field contract. It is not another
assembler. Alignment is an explicit, synthetic-only copy operation; original
files, unresolved dependencies and acceptance records are never changed in place.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

try:
    from .verify import SOURCE_BLOBS
except ImportError:
    from verify import SOURCE_BLOBS

UPSTREAM_COMMIT = "9854aadbef7d33d792a1befbbbaac451e694fde0"
UPSTREAM_BLOB = "769aacac16606deaaf08f74fb1ff184c0da6cc85"
UPSTREAM_PATH = "revenue/uiowa_rfq_18649_milestone_packets/fixtures/engagement.json"
PROFILE = "uiowa-18649-proposed-workshare-40-40-20"
TERMS = {
    "KICKOFF": (960_000, 40, "WRITTEN_AUTHORIZATION", "written authorization/kickoff"),
    "DRAFT_DELIVERY": (960_000, 40, "DRAFT_DELIVERY", "delivery of the draft technical work package"),
    "FINAL_ACCEPTANCE": (480_000, 20, "FINAL_ACCEPTANCE", "acceptance of the final technical work package"),
}
KNOWN_OPTION = ("IDX-M3-003", "final/readout-deck-outline.md")
BOUNDARY = "SYNTHETIC PREPARATION ONLY. PROPOSED / NOT ACCEPTED. No invoice, payment, acceptance, authorization or revenue is established."


def cents(raw: Any) -> int:
    """Match the producer's integer-cents / explicit-dollar-string convention."""
    if type(raw) is int:
        return raw
    if not isinstance(raw, str):
        raise ValueError("amount must be integer cents or explicit dollar text")
    match = re.fullmatch(r"\$?((?:\d{1,3}(?:,\d{3})+)|\d+)\.(\d{2})", raw.strip())
    if not match:
        raise ValueError("dollar text needs valid grouping and exactly two decimals")
    return int(match[1].replace(",", "")) * 100 + int(match[2])


def money(value: int) -> str:
    return f"{value // 100:,}.{value % 100:02d}"


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read(path: Path) -> dict:
    def invalid(value):
        raise ValueError(f"nonfinite JSON number: {value}")
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs, parse_constant=invalid)
    if not isinstance(data, dict):
        raise ValueError("engagement must be a JSON object")
    return data


def dump(data) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def check(plan: dict) -> dict:
    diagnostics = []
    def add(code, locator, observed, expected):
        diagnostics.append({"code": code, "locator": locator, "observed": observed, "expected": expected})
    if not isinstance(plan, dict) or plan.get("synthetic") is not True:
        raise ValueError("this public rehearsal adapter requires synthetic=true")
    optional = plan.get("separate_optional_items", [])
    if not isinstance(optional, list) or any(not isinstance(x, dict) for x in optional):
        raise ValueError("separate_optional_items must be an object array")
    records = plan.get("milestones")
    if not isinstance(records, list) or any(not isinstance(m, dict) for m in records):
        raise ValueError("milestones must be an object array")
    try:
        total = cents(plan.get("contract_total"))
    except ValueError as e:
        total = None
        add("INVALID_TOTAL", "/contract_total", str(e), "2400000 integer cents")
    if total is not None and total != 2_400_000:
        add("BASE_AMOUNT_MISMATCH", "/contract_total", total, 2_400_000)
    kinds = [m.get("kind") for m in records]
    if len(kinds) != 3 or set(k for k in kinds if isinstance(k, str)) != set(TERMS):
        add("MILESTONE_SET_MISMATCH", "/milestones", kinds, list(TERMS))
    identifiers = [m.get("milestone_id") for m in records]
    if any(not isinstance(i, str) or not i.strip() for i in identifiers) or len({str(i) for i in identifiers}) != len(identifiers):
        add("MILESTONE_ID_INVALID", "/milestones", identifiers, "unique nonempty IDs")
    measured = []
    for index, m in enumerate(records):
        loc = f"/milestones/{index}"
        kind = m.get("kind")
        spec = TERMS.get(kind) if isinstance(kind, str) else None
        try:
            amount = cents(m.get("amount"))
        except ValueError as e:
            amount = None
            add("INVALID_AMOUNT", loc + "/amount", str(e), "integer cents or explicit dollars")
        if spec is None:
            continue
        expected, percent, trigger, description = spec
        measured.append(amount)
        if amount is not None and amount != expected:
            add("MILESTONE_AMOUNT_MISMATCH", loc + "/amount", amount, expected)
        stated = m.get("invoice_description")
        percentages = re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%", stated) if isinstance(stated, str) else []
        if percentages != [str(percent)]:
            add("DESCRIPTION_SHARE_MISMATCH", loc + "/invoice_description", percentages, [str(percent)])
        if m.get("payment_trigger") != trigger:
            add("TRIGGER_NOT_BOUND_TO_PROPOSAL", loc + "/payment_trigger", m.get("payment_trigger"), trigger)
        items = m.get("index_items")
        if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
            raise ValueError(loc + "/index_items must be an object array")
        for i, item in enumerate(items):
            label = str(item.get("title", "")).casefold()
            pair = (item.get("item_id"), item.get("path"))
            if pair == KNOWN_OPTION or "optional readout" in label:
                add("OPTION_INSIDE_BASE_PACKET", loc + f"/index_items/{i}", item.get("path"), "Separate optional-readout collection; not a base deliverable")
    summed = sum(measured) if len(measured) == 3 and all(type(x) is int for x in measured) else None
    if summed is not None and summed != total:
        add("TOTAL_DOES_NOT_RECONCILE", "/milestones", summed, total)
    basis = plan.get("proposal_basis")
    expected_basis = {"profile": PROFILE, "status": "PROPOSED_NOT_ACCEPTED", "source_blobs": SOURCE_BLOBS}
    if basis != expected_basis:
        add("PROPOSAL_BASIS_UNBOUND", "/proposal_basis", basis, expected_basis)
    return {"boundary": BOUNDARY, "profile": PROFILE,
            "aligned_with_bound_proposed_terms": not diagnostics,
            "declared_total_cents": total, "milestone_total_cents": summed,
            "base_total_alone_is_sufficient": False,
            "invoice_issued": False, "payment_due": "NOT_DETERMINED",
            "diagnostics": diagnostics}


def align_synthetic(plan: dict) -> tuple[dict, list[dict]]:
    """Return a reviewable copy, preserving all original evidence and unknowns."""
    check(plan)
    out = copy.deepcopy(plan)
    records = out["milestones"]
    if len(records) != 3 or set(m.get("kind") for m in records) != set(TERMS):
        raise ValueError("alignment requires exactly the three recognized milestone kinds")
    edits = []
    def set_value(obj, key, value, locator):
        old = copy.deepcopy(obj.get(key))
        if old != value:
            edits.append({"locator": locator, "before": old, "after": copy.deepcopy(value)})
            obj[key] = value
    set_value(out, "contract_total", "24,000.00", "/contract_total")
    set_value(out, "proposal_basis", {"profile": PROFILE, "status": "PROPOSED_NOT_ACCEPTED", "source_blobs": SOURCE_BLOBS}, "/proposal_basis")
    optional = list(out.get("separate_optional_items", []))
    for index, m in enumerate(records):
        amount, pct, trigger, description = TERMS[m["kind"]]
        loc = f"/milestones/{index}"
        set_value(m, "amount", money(amount), loc + "/amount")
        set_value(m, "payment_trigger", trigger, loc + "/payment_trigger")
        set_value(m, "invoice_description", f"DRAFT DESCRIPTION ONLY: {m['milestone_id']} — {pct}% ({money(amount)} USD) on {description}; proposed technical assessment workshare. Not an issued invoice or amount determined due.", loc + "/invoice_description")
        retained = []
        for item_index, item in enumerate(m["index_items"]):
            pair = (item.get("item_id"), item.get("path"))
            if pair == KNOWN_OPTION:
                if item.get("criteria_ids"):
                    raise ValueError("optional example is bound to a base criterion; human reconciliation required")
                if any(item.get("item_id") in c.get("evidence_item_ids", []) for c in m.get("criteria", [])):
                    raise ValueError("a base criterion cites the optional item; human reconciliation required")
                optional.append(copy.deepcopy(item))
                edits.append({"locator": loc + f"/index_items/{item_index}", "action": "moved_without_discarding_record", "destination": "/separate_optional_items"})
            else:
                retained.append(item)
        m["index_items"] = retained
    if optional:
        out["separate_optional_items"] = optional
    return out, edits


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("engagement", type=Path)
    p.add_argument("--output-dir", type=Path, help="Write report and an explicitly aligned synthetic COPY to a new directory")
    args = p.parse_args(argv)
    try:
        source = args.engagement.read_bytes()
        plan = read(args.engagement)
        result = check(plan)
        result["input_git_blob"] = blob(source)
        result["input_sha256"] = hashlib.sha256(source).hexdigest()
        if args.output_dir is not None:
            out = args.output_dir.resolve()
            if out.exists():
                raise ValueError("output exists; choose a new directory")
            aligned, changes = align_synthetic(plan)
            after = check(aligned)
            out.mkdir(parents=True, exist_ok=False)
            for name, data in [("before.json", result), ("aligned-engagement.json", aligned), ("after.json", after), ("changes.json", changes)]:
                (out / name).write_text(dump(data), encoding="utf-8")
        print(dump(result), end="")
        return 0 if result["aligned_with_bound_proposed_terms"] else 1
    except (ValueError, OSError, TypeError, KeyError) as exc:
        p.exit(2, f"profile input/output error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
