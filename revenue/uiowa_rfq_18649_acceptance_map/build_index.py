#!/usr/bin/env python3
"""UIOWA-130 - map delivery acceptance criteria to the artifacts that demonstrate them.

Reads the real ACCEPTANCE_EXHIBIT.md, runs a declared content check for each numbered
acceptance criterion against artifacts actually on disk, and emits a linked acceptance
index plus a checked sample delivery packet.

The point of the exercise is the SPLIT, not the total. A criterion is only
DEMONSTRABLE when a check ran and passed and the observed value is recorded. Criteria
that need a prospective prime, a review window, or real University evidence are
reported as NEEDS_ENGAGEMENT_EVIDENCE with the missing input named. Marking those met
would defeat the purpose of the index.

This package is READ-ONLY against every other lane. It never writes outside its own
output directory.

Python 3 standard library only. No network beyond nothing at all.

    python3 build_index.py --revenue-root .. --out output
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

import checks as C
import exhibit_parser

STATUSES = ("DEMONSTRABLE", "PARTIAL", "NOT_DEMONSTRATED",
            "NEEDS_ENGAGEMENT_EVIDENCE", "UNMAPPED")

BANNER = (
    "ARTIFACT CONFORMANCE EVIDENCE ONLY. The workshare this index refers to is "
    "PROPOSED / NOT ACCEPTED. Nothing here represents that the University of Iowa "
    "accepted any conclusion, that a subcontract was executed, or that any payment "
    "occurred. Supporting fixtures are synthetic and are not University findings."
)


def derive_status(results, required_inputs, bound):
    """Earned, not asserted. Every branch is reachable from the shipped map."""
    if not bound:
        return "UNMAPPED", "no binding declared for this criterion"
    if not results:
        return ("NEEDS_ENGAGEMENT_EVIDENCE",
                "no artifact in this repository can demonstrate this criterion")
    p = sum(1 for r in results if r["outcome"] == C.PASS)
    f = sum(1 for r in results if r["outcome"] == C.FAIL)
    u = sum(1 for r in results if r["outcome"] == C.UNAVAILABLE)
    summary = f"{p} passed, {f} failed, {u} unavailable"
    if p and not f and not u:
        if required_inputs:
            return "PARTIAL", summary + "; part of this criterion still needs engagement evidence"
        return "DEMONSTRABLE", summary
    if p:
        return "PARTIAL", summary
    if f:
        return "NOT_DEMONSTRATED", summary
    return "UNMAPPED", summary + "; the bound artifacts are not present"


def build(revenue_root, exhibit_path, map_path):
    exhibit = exhibit_parser.parse_exhibit(exhibit_path)
    with open(map_path, encoding="utf-8") as fh:
        mapping = json.load(fh)
    bindings = mapping["bindings"]
    dl_bindings = mapping.get("deliverable_bindings", {})

    entries = []
    for crit in exhibit["criteria"]:
        cid = crit["criterion_id"]
        binding = bindings.get(cid)
        results = []
        if binding:
            for spec in binding.get("checks", []):
                outcome, detail = C.run_check(revenue_root, spec)
                results.append({
                    "label": spec.get("label", spec["kind"]),
                    "kind": spec["kind"],
                    "target": spec.get("params", {}).get("path")
                              or " ".join(spec.get("params", {}).get("argv", [])),
                    "outcome": outcome,
                    "observed": detail,
                })
        required = (binding or {}).get("required_engagement_inputs", [])
        status, basis = derive_status(results, required, binding is not None)
        entries.append({**crit, "status": status, "status_basis": basis,
                        "checks": results, "required_engagement_inputs": required})

    deliverables = []
    for dl in exhibit["deliverables"]:
        did = dl["deliverable_id"]
        binding = dl_bindings.get(did)
        results = []
        if binding:
            for spec in binding.get("checks", []):
                outcome, detail = C.run_check(revenue_root, spec)
                results.append({"label": spec.get("label", spec["kind"]),
                                "kind": spec["kind"],
                                "target": spec.get("params", {}).get("path", ""),
                                "outcome": outcome, "observed": detail})
        required = (binding or {}).get("required_engagement_inputs", [])
        status, basis = derive_status(results, required, binding is not None)
        deliverables.append({**dl, "status": status, "status_basis": basis,
                             "checks": results, "required_engagement_inputs": required})

    tally = {s: 0 for s in STATUSES}
    for e in entries:
        tally[e["status"]] += 1
    dl_tally = {s: 0 for s in STATUSES}
    for d in deliverables:
        dl_tally[d["status"]] += 1

    return {
        "_banner": BANNER,
        "index": "UIOWA-130 acceptance criteria to artifact index",
        "exhibit": {
            "path": os.path.relpath(exhibit_path, revenue_root),
            "digest_sha256": exhibit["digest_sha256"],
            "commercial_status": exhibit["commercial_status"],
            "criteria_extracted": len(exhibit["criteria"]),
            "deliverable_items_extracted": len(exhibit["deliverables"]),
        },
        "statuses": list(STATUSES),
        "criterion_tally": tally,
        "deliverable_tally": dl_tally,
        "criteria": entries,
        "deliverables": deliverables,
    }


def authored_prose(index):
    """Return only the prose THIS package wrote, never text quoted from the exhibit.

    Needed because the forbidden-representation guard is a substring scan, and the
    exhibit's own criterion 5.3.5 contains the phrase "the University accepted a
    conclusion" inside a prohibition. Quoting a rule is not breaking it. Scanning the
    rendered document naively flags its own source text, so the guard runs against the
    fields this package authored: the banner, derived statuses and bases, check labels
    and observed values, and the named missing inputs.
    """
    parts = [index["_banner"], index["index"]]
    for entry in list(index["criteria"]) + list(index["deliverables"]):
        parts.append(entry["status"])
        parts.append(entry["status_basis"])
        parts.extend(entry["required_engagement_inputs"])
        for chk in entry["checks"]:
            parts.extend([chk["label"], chk["observed"], str(chk.get("target") or "")])
    return "\n".join(parts)


PACKET_MARKER = "UIOWA-130 checked sample delivery packet"


class UnsafePacketDirectory(Exception):
    """Raised rather than recursively deleting a directory we cannot prove is ours."""


def _clear_our_packet_dir(packet_dir):
    """Remove a previous packet, but only one this tool can prove it wrote.

    Reported by seat OP5-MARROW's destructive-call screen, which classified the old
    unconditional shutil.rmtree here as REVIEW_REQUIRED because its path descends from
    --out, an argv value. The screen was right: `--out <somewhere real>` would have
    recursively deleted `<somewhere real>/sample_packet` with no check that this tool
    created it. A rebuild now refuses unless the directory is empty or carries our own
    MANIFEST.json marker, so an unrelated directory that happens to share the name is
    never destroyed.
    """
    if not os.path.isdir(packet_dir):
        return
    entries = os.listdir(packet_dir)
    if not entries:
        os.rmdir(packet_dir)
        return
    manifest = os.path.join(packet_dir, "MANIFEST.json")
    if os.path.isfile(manifest):
        try:
            with open(manifest, encoding="utf-8") as fh:
                if json.load(fh).get("packet") == PACKET_MARKER:
                    shutil.rmtree(packet_dir)
                    return
        except (ValueError, OSError):
            pass
    raise UnsafePacketDirectory(
        f"{packet_dir} exists and is not recognisably a packet this tool wrote "
        f"(no MANIFEST.json carrying {PACKET_MARKER!r}); refusing to delete "
        f"{len(entries)} item(s). Choose a different --out, or remove it yourself.")


def sample_packet(index, revenue_root, out_dir):
    """Assemble a packet from artifacts that verification actually showed demonstrable.

    An artifact only enters the packet if a check on it PASSED. Nothing is included on
    the strength of being mentioned in a map.
    """
    packet_dir = os.path.join(out_dir, "sample_packet")
    _clear_our_packet_dir(packet_dir)
    os.makedirs(packet_dir)
    included, skipped = [], []
    for entry in index["criteria"]:
        for chk in entry["checks"]:
            target = chk.get("target") or ""
            src = os.path.join(revenue_root, target)
            if not target or not os.path.isfile(src):
                continue
            if chk["outcome"] != C.PASS:
                skipped.append({"criterion_id": entry["criterion_id"], "path": target,
                                "outcome": chk["outcome"], "observed": chk["observed"]})
                continue
            flat = target.replace("/", "__").replace(os.sep, "__")
            dest = os.path.join(packet_dir, flat)
            if not os.path.isfile(dest):
                shutil.copy2(src, dest)
            with open(dest, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            included.append({"criterion_id": entry["criterion_id"],
                             "source_path": target, "packet_file": flat,
                             "sha256": digest, "demonstrates": chk["label"]})
    included.sort(key=lambda r: (r["criterion_id"], r["packet_file"]))
    skipped.sort(key=lambda r: (r["criterion_id"], r["path"]))
    manifest = {
        "_banner": BANNER,
        "packet": PACKET_MARKER,
        "rule": "a file is included only when a check against it returned PASS",
        "exhibit_digest_sha256": index["exhibit"]["digest_sha256"],
        "included": included,
        "excluded_because_the_check_did_not_pass": skipped,
        "files_included": len({r["packet_file"] for r in included}),
    }
    with open(os.path.join(packet_dir, "MANIFEST.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def render_markdown(index, manifest):
    L = []
    a = L.append
    a("# UIOWA-130 — acceptance criteria to artifact index")
    a("")
    a("> **" + BANNER + "**")
    a("")
    ex = index["exhibit"]
    a(f"Source of the criteria: `{ex['path']}` @ sha256 `{ex['digest_sha256'][:16]}…` — "
      f"commercial status **{ex['commercial_status']}**. "
      f"{ex['criteria_extracted']} numbered acceptance criteria and "
      f"{ex['deliverable_items_extracted']} deliverable items were extracted from that "
      f"file, not transcribed by hand.")
    a("")
    a("## How to read the status column")
    a("")
    a("| Status | Meaning |")
    a("| --- | --- |")
    a("| `DEMONSTRABLE` | A check ran against a real artifact and passed. The observed "
      "value is recorded below. |")
    a("| `PARTIAL` | Some of the criterion is shown by an artifact; the rest is not. |")
    a("| `NOT_DEMONSTRATED` | A check ran and **failed**. The artifact exists and does not "
      "meet the criterion. |")
    a("| `NEEDS_ENGAGEMENT_EVIDENCE` | No file in this repository can demonstrate it. It "
      "needs a prime, a review window, or real University evidence. |")
    a("| `UNMAPPED` | No binding, or the bound artifacts are not on disk. |")
    a("")
    t = index["criterion_tally"]
    a("Criterion tally: " + ", ".join(f"**{k}** {t[k]}" for k in index["statuses"]) + ".")
    a("")
    a("## 1. Acceptance criteria")
    a("")
    a("| Criterion | Package | Status | Basis |")
    a("| --- | --- | --- | --- |")
    for e in index["criteria"]:
        a(f"| `{e['criterion_id']}` | {e['section']} | **{e['status']}** | {e['status_basis']} |")
    a("")
    a("## 2. Each criterion, with what was actually observed")
    a("")
    for e in index["criteria"]:
        a(f"### `{e['criterion_id']}` — {e['status']}")
        a("")
        a(f"> {e['text']}")
        a("")
        if e["checks"]:
            a("| Check | Target | Outcome | Observed |")
            a("| --- | --- | --- | --- |")
            for c in e["checks"]:
                a(f"| {c['label']} | `{c['target']}` | **{c['outcome']}** | {c['observed']} |")
            a("")
        if e["required_engagement_inputs"]:
            a("Still needs engagement evidence:")
            a("")
            for r in e["required_engagement_inputs"]:
                a(f"- {r}")
            a("")
    a("## 3. Deliverable items")
    a("")
    dt = index["deliverable_tally"]
    a("Deliverable tally: " + ", ".join(f"**{k}** {dt[k]}" for k in index["statuses"]) + ".")
    a("")
    a("| Item | Section | Status | Text |")
    a("| --- | --- | --- | --- |")
    for d in index["deliverables"]:
        a(f"| `{d['deliverable_id']}` | {d['section']} | **{d['status']}** | {d['text'][:88]} |")
    a("")
    a("## 4. Checked sample delivery packet")
    a("")
    a(f"`output/sample_packet/` holds **{manifest['files_included']} files**, each included "
      f"only because a check against it returned PASS. "
      f"{len(manifest['excluded_because_the_check_did_not_pass'])} bound artifact(s) were "
      f"excluded because their check did not pass; they are listed in `MANIFEST.json` with "
      f"the reason rather than dropped.")
    a("")
    a("## 5. What this index does not say")
    a("")
    a("- It does not say the workshare was accepted. The exhibit reads "
      f"**{ex['commercial_status']}**.")
    a("- It does not say the University agreed with anything, that a subcontract exists, "
      "or that any payment occurred.")
    a("- A `DEMONSTRABLE` criterion means an artifact met a stated condition. It is not a "
      "score, a rating, a certification, or a professional judgement.")
    a("- Supporting fixtures in the bound lanes are synthetic. No real University record "
      "has been observed.")
    a("")
    return "\n".join(L)


def _csv(fieldnames, rows):
    import csv as _c
    import io
    buf = io.StringIO(newline="")
    buf.write("# " + BANNER + "\n")
    w = _c.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--revenue-root", default="..",
                   help="directory holding the uiowa_rfq_18649_* lanes (default: ..)")
    p.add_argument("--exhibit", default=None, help="path to ACCEPTANCE_EXHIBIT.md")
    p.add_argument("--map", default="acceptance_map.json")
    p.add_argument("--out", default="output")
    args = p.parse_args(argv)

    exhibit = args.exhibit or os.path.join(
        args.revenue_root, "uiowa_rfq_18649_workshare", "ACCEPTANCE_EXHIBIT.md")
    if not os.path.isfile(exhibit):
        print(f"EXHIBIT NOT FOUND: {exhibit}", file=sys.stderr)
        return 2

    index = build(args.revenue_root, exhibit, args.map)
    os.makedirs(args.out, exist_ok=True)
    try:
        manifest = sample_packet(index, args.revenue_root, args.out)
    except UnsafePacketDirectory as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3

    with open(os.path.join(args.out, "acceptance_index.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(index, indent=2, sort_keys=True) + "\n")
    with open(os.path.join(args.out, "acceptance_index.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write(_csv(["criterion_id", "section", "status", "status_basis",
                       "checks_run", "text"],
                      [{**e, "checks_run": len(e["checks"])} for e in index["criteria"]]))
    needs = [{"criterion_id": e["criterion_id"], "section": e["section"],
              "status": e["status"], "missing_input": r}
             for e in index["criteria"] for r in e["required_engagement_inputs"]]
    with open(os.path.join(args.out, "needs_engagement_evidence.csv"), "w",
              encoding="utf-8", newline="") as fh:
        fh.write(_csv(["criterion_id", "section", "status", "missing_input"], needs))
    with open(os.path.join(args.out, "ACCEPTANCE_INDEX.md"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(render_markdown(index, manifest))

    print(BANNER)
    print("")
    print(f"exhibit        {index['exhibit']['path']}")
    print(f"               sha256 {index['exhibit']['digest_sha256'][:16]}  "
          f"status {index['exhibit']['commercial_status']}")
    print(f"criteria       {index['exhibit']['criteria_extracted']} extracted")
    for s in STATUSES:
        print(f"  {s:<26} {index['criterion_tally'][s]}")
    print(f"deliverables   {index['exhibit']['deliverable_items_extracted']} extracted")
    for s in STATUSES:
        if index["deliverable_tally"][s]:
            print(f"  {s:<26} {index['deliverable_tally'][s]}")
    print("")
    print(f"sample packet  {manifest['files_included']} files included, "
          f"{len(manifest['excluded_because_the_check_did_not_pass'])} excluded for not passing")
    print(f"written to     {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
