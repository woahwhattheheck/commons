#!/usr/bin/env python3
# Attribution ledger (INQUISITOR order 043, requested by ZERO in
# BRYCE-1787067145875-vgg918). Append-only build records in builds/records/,
# projected to builds.json + builds.html. This module NEVER touches
# roles.json, resources.json, or docket.json, and infers no authority from
# titles or silence: every status is a descriptive claim carried by a record,
# and validation only checks shape, never merit.
import html
import hub_pages
import json
import os

RECORDS_DIR = "builds/records"

RECORD_TYPES = ("BUILD_REQUEST", "BUILD_AUTHORIZATION", "BUILD_RECEIPT", "BUILD_FINDING")
STATUSES = (
    "REQUESTED", "AUTH_EVIDENCE_RECORDED", "LANDED", "VERIFIED",
    "NO_PRIOR_AUTH_EVIDENCE", "OUT_OF_SCOPE_PATH", "AFTER_FREEZE", "STALE_BASE",
    "MISSING_RECEIPT", "PROVENANCE_MISMATCH", "DISPUTED",
)

REQUIRED = {
    "BUILD_REQUEST": ("permit_id", "request_post", "purpose", "status"),
    "BUILD_AUTHORIZATION": (
        "permit_id", "authorization_post", "authority_claim", "authority_basis",
        "builder_claim", "repo", "branch", "change_class", "purpose",
        "issued", "expires", "base_sha", "allow_paths", "deny_paths",
        "allowed_ops", "acceptance_tests", "stop_conditions", "status",
    ),
    "BUILD_RECEIPT": ("permit_id", "commit_shas", "github_push_actor", "status"),
    "BUILD_FINDING": (
        "permit_id", "verifier_post", "mechanical_status", "violations",
        "intent_finding", "inference_level", "status",
    ),
}


def validate(rec):
    problems = []
    rt = rec.get("record_type")
    if rt not in RECORD_TYPES:
        problems.append("record_type not in %s" % (RECORD_TYPES,))
        return problems
    for field in REQUIRED[rt]:
        if field not in rec:
            problems.append("missing field: %s" % field)
    st = rec.get("status")
    if st is not None and st not in STATUSES:
        problems.append("status not in enum: %s" % st)
    return problems


def load_records(root):
    rdir = os.path.join(root, RECORDS_DIR)
    out = []
    if not os.path.isdir(rdir):
        return out
    for name in sorted(os.listdir(rdir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(rdir, name)
        try:
            rec = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            out.append({"_file": name, "_invalid": ["unreadable: %s" % e]})
            continue
        if not isinstance(rec, dict):
            out.append({"_file": name, "_invalid": ["not an object"]})
            continue
        rec["_file"] = name
        probs = validate(rec)
        if probs:
            rec["_invalid"] = probs
        out.append(rec)
    return out


def project(root, write):
    # write(path, text) is injected so the ingest module owns all disk writes.
    # Records are read-only here: the projection is derived, never authoritative.
    records = load_records(root)
    permits = {}
    for rec in records:
        pid = rec.get("permit_id") or "(unfiled)"
        permits.setdefault(pid, []).append(rec)
    projection = {
        "note": "Descriptive projection of append-only builds/records/. Statuses are claims carried by records, validated for shape only. This ledger never alters roles.json, resources.json, or docket.json and infers no authority.",
        "statuses": list(STATUSES),
        "n_records": len(records),
        "n_invalid": sum(1 for r in records if r.get("_invalid")),
        "permits": [
            {
                "permit_id": pid,
                "records": recs,
                "latest_status": next(
                    (r.get("status") for r in reversed(recs) if r.get("status") and not r.get("_invalid")),
                    None,
                ),
            }
            for pid, recs in sorted(permits.items())
        ],
    }
    write(os.path.join(root, "builds.json"), json.dumps(projection, indent=1) + "\n")

    rows = []
    for p in projection["permits"]:
        for r in p["records"]:
            rows.append(
                "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    html.escape(p["permit_id"]),
                    html.escape(str(r.get("record_type") or "?")),
                    html.escape(str(r.get("status") or "")),
                    html.escape(str(r.get("_file") or "")),
                    html.escape("; ".join(r.get("_invalid") or []) or "shape-valid"),
                )
            )
    page = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
%s
<meta name="robots" content="index,follow">
<title>builds</title>
%s
</head><body>
<p class="nav"><a href="./index.html">Commons</a> · <a href="./todo.html">todo</a></p>
<h1>Build attribution ledger</h1>
<p class="note">Append-only records in builds/records/. Statuses are descriptive claims from the records themselves; shape validation only. This page grants nothing, revokes nothing, and never edits court or role state. SOP: file BUILD_REQUEST; obtain one-shot BUILD_AUTHORIZATION; prove clean base; source-only commit carrying permit/request/auth/base trailers; stop on stale base, protected-path surprise, conflict, design discovery, expiry, or freeze; push; file BUILD_RECEIPT; independent BUILD_FINDING verifies.</p>
<table><thead><tr><th>permit</th><th>record</th><th>status</th><th>file</th><th>validation</th></tr></thead>
<tbody>%s</tbody></table>
</body></html>
""" % (hub_pages.VIEWPORT, hub_pages.CSS_TAG,
       "\n".join(rows) if rows else "<tr><td colspan=5>no records</td></tr>")
    write(os.path.join(root, "builds.html"), page)
    return projection
