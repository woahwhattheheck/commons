"""Materialize approved internal receipts into the response-module catalog.

Companion to engine.py. Internal owner-review evidence preparation only.
Certification/reference/SLA/security assertions without supported receipts
remain non-SUPPORTED so the compiler HOLDs. No buyer contact, submission,
signature, pricing, payment, award, or revenue.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from revenue.procurement_response_module_library.engine import (
    BOUNDARY,
    Error,
    LIB,
    canon,
    digest,
    dt,
    i,
    keys,
    load,
    s,
    sh,
    toks,
    b,
)

MAT = "procurement-response-modules/materializer/v1"
DIFF = "procurement-response-modules/materializer-diff/v1"
REC = "procurement-response-modules/materializer-receipt/v1"
KINDS = {"EVIDENCE", "POLICY", "CAPABILITY"}
ESTAT = {"SUPPORTED", "PARTIAL", "MISSING", "NOT_APPLICABLE"}
OSTAT = {"APPROVED", "PENDING", "DENIED"}
ASSERT = {"GENERAL", "CERTIFICATION", "REFERENCE", "SLA", "SECURITY"}
RESTRICTED = {"CERTIFICATION", "REFERENCE", "SLA", "SECURITY"}


def authority():
    return {k: False for k in [
        "submission_authorized", "buyer_contact_authorized", "signature_authorized",
        "certification_authorized", "price_commitment_authorized", "payment_authorized",
        "award_or_revenue_recognized",
    ]}


def _norm_receipt(x, n, now):
    w = f"receipts[{n}]"
    keys(x, [
        "receipt_id", "kind", "ref", "sha256", "observed_at", "status", "summary",
        "family", "tags", "owner_status", "claim_id", "claim_text", "valid_from",
        "valid_until", "assertion_class", "module_id", "revision",
    ], w)
    kind = s(x["kind"], w + ".kind", True, 32)
    if kind not in KINDS:
        raise Error(w + ": bad kind")
    status = s(x["status"], w + ".status", True, 32)
    if status not in ESTAT:
        raise Error(w + ": bad status")
    owner = s(x["owner_status"], w + ".owner_status", True, 32)
    if owner not in OSTAT:
        raise Error(w + ": bad owner_status")
    aclass = s(x["assertion_class"], w + ".assertion_class", True, 32)
    if aclass not in ASSERT:
        raise Error(w + ": bad assertion_class")
    if aclass in RESTRICTED and status == "SUPPORTED":
        raise Error(w + ": unsupported certification/reference/SLA/security cannot be SUPPORTED")
    obs = dt(x["observed_at"], w + ".observed_at")
    if obs > now:
        raise Error(w + ": future evidence")
    vf = dt(x["valid_from"], w + ".valid_from")
    vu = dt(x["valid_until"], w + ".valid_until")
    if not vf <= now <= vu:
        raise Error(w + ": outside validity window")
    return {
        "receipt_id": s(x["receipt_id"], w + ".receipt_id", True),
        "kind": kind,
        "ref": s(x["ref"], w + ".ref", limit=2048),
        "sha256": sh(x["sha256"], w + ".sha256"),
        "observed_at": obs,
        "status": status,
        "summary": s(x["summary"], w + ".summary", limit=1024),
        "family": s(x["family"], w + ".family", True),
        "tags": toks(x["tags"], w + ".tags"),
        "owner_status": owner,
        "claim_id": s(x["claim_id"], w + ".claim_id", True),
        "claim_text": s(x["claim_text"], w + ".claim_text"),
        "valid_from": vf,
        "valid_until": vu,
        "assertion_class": aclass,
        "module_id": s(x["module_id"], w + ".module_id", True),
        "revision": i(x["revision"], w + ".revision", 1, 10**6),
    }


def materialize(raw: bytes, base_raw: bytes | None = None):
    v = load(raw, "materializer")
    keys(v, ["schema", "library_id", "generated_at", "evidence_max_age_seconds", "truth_boundary", "receipts"], "materializer")
    if v["schema"] != MAT or v["truth_boundary"] != BOUNDARY:
        raise Error("materializer: unsupported schema/boundary")
    now = dt(v["generated_at"], "materializer.generated_at")
    maxage = i(v["evidence_max_age_seconds"], "materializer.evidence_max_age_seconds", 1, 31536000)
    if not isinstance(v["receipts"], list) or not v["receipts"]:
        raise Error("materializer: receipts required")
    recs = [_norm_receipt(x, n, now) for n, x in enumerate(v["receipts"])]
    ids = [x["receipt_id"] for x in recs]
    if len(ids) != len(set(ids)):
        raise Error("materializer: duplicate receipt_id")
    evidence = []
    modules = {}
    for r in recs:
        evidence.append({
            "evidence_id": r["receipt_id"],
            "ref": r["ref"],
            "sha256": r["sha256"],
            "observed_at": r["observed_at"],
            "status": r["status"],
            "summary": r["summary"],
        })
        key = (r["module_id"], r["revision"])
        mod = modules.setdefault(key, {
            "module_id": r["module_id"],
            "revision": r["revision"],
            "family": r["family"],
            "title": r["module_id"].replace("-", " "),
            "tags": list(r["tags"]),
            "owner_status": r["owner_status"],
            "valid_from": r["valid_from"],
            "valid_until": r["valid_until"],
            "source_ref": r["ref"],
            "source_sha256": r["sha256"],
            "claims": [],
            "_families": {r["family"]},
            "_owners": {r["owner_status"]},
        })
        mod["_families"].add(r["family"])
        mod["_owners"].add(r["owner_status"])
        if r["owner_status"] != "APPROVED":
            mod["owner_status"] = r["owner_status"] if mod["owner_status"] == "APPROVED" else (
                "DENIED" if "DENIED" in mod["_owners"] else "PENDING"
            )
        mod["tags"] = sorted(set(mod["tags"]) | set(r["tags"]))
        mod["claims"].append({"claim_id": r["claim_id"], "text": r["claim_text"], "evidence_ids": [r["receipt_id"]]})
    for mod in modules.values():
        if len(mod["_families"]) != 1:
            raise Error("materializer: mixed families in one module")
        del mod["_families"]
        del mod["_owners"]
        cids = [c["claim_id"] for c in mod["claims"]]
        if len(cids) != len(set(cids)):
            raise Error("materializer: duplicate claim_id")
        mod["claims"] = sorted(mod["claims"], key=lambda c: c["claim_id"])
    catalog = {
        "schema": LIB,
        "library_id": s(v["library_id"], "library_id", True),
        "generated_at": now,
        "evidence_max_age_seconds": maxage,
        "truth_boundary": BOUNDARY,
        "evidence": sorted(evidence, key=lambda x: x["evidence_id"]),
        "modules": sorted(modules.values(), key=lambda m: (m["family"], m["module_id"], m["revision"])),
    }
    cb = canon(catalog)
    prev = None
    if base_raw is not None:
        prev = load(base_raw, "base-catalog")
    added_e = [x["evidence_id"] for x in catalog["evidence"]]
    removed_e = []
    if prev:
        old_e = {x["evidence_id"] for x in prev.get("evidence", []) if isinstance(prev.get("evidence"), list) and isinstance(x, dict) and "evidence_id" in x}
        new_e = {x["evidence_id"] for x in catalog["evidence"]}
        added_e = sorted(new_e - old_e)
        removed_e = sorted(old_e - new_e)
    diff = {
        "schema": DIFF,
        "truth_boundary": BOUNDARY,
        "library_id": catalog["library_id"],
        "added_evidence_ids": added_e if prev else [x["evidence_id"] for x in catalog["evidence"]],
        "removed_evidence_ids": removed_e,
        "module_count": len(catalog["modules"]),
        "authority": authority(),
    }
    db = canon(diff)
    rec = {
        "schema": REC,
        "truth_boundary": BOUNDARY,
        "library_id": catalog["library_id"],
        "input_sha256": digest(raw),
        "catalog_sha256": digest(cb),
        "diff_sha256": digest(db),
        "authority": authority(),
    }
    return cb, db, canon(rec)


def verify(raw, catalog, diff, receipt, base_raw=None):
    exp_c, exp_d, exp_r = materialize(raw, base_raw)
    if canon(load(catalog, "catalog")) != catalog:
        raise Error("catalog non-canonical")
    if catalog != exp_c or diff != exp_d or receipt != exp_r:
        raise Error("materializer mismatch")
    return {"verified": True, "catalog_sha256": digest(exp_c)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("compile")
    c.add_argument("--receipts", required=True)
    c.add_argument("--out-dir", required=True)
    c.add_argument("--base-catalog")
    v = sp.add_parser("verify")
    v.add_argument("--receipts", required=True)
    v.add_argument("--catalog", required=True)
    v.add_argument("--diff", required=True)
    v.add_argument("--receipt", required=True)
    v.add_argument("--base-catalog")
    a = ap.parse_args(argv)
    try:
        rb = lambda p: Path(p).read_bytes()
        if a.cmd == "compile":
            base = rb(a.base_catalog) if a.base_catalog else None
            cat, diff, rec = materialize(rb(a.receipts), base)
            out = Path(a.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / "catalog.json").write_bytes(cat)
            (out / "diff.json").write_bytes(diff)
            (out / "receipt.json").write_bytes(rec)
            print(json.dumps({"catalog_sha256": digest(cat)}, sort_keys=True))
        else:
            base = rb(a.base_catalog) if a.base_catalog else None
            print(json.dumps(verify(rb(a.receipts), rb(a.catalog), rb(a.diff), rb(a.receipt), base), sort_keys=True))
        return 0
    except (Error, OSError) as e:
        print(f"HOLD: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
