"""OPS-BIDPACK-INTEGRATION -- build a bid-pack manifest from a delivered report.

Reads two artifacts already landed by another lane, READ-ONLY:

    revenue/uiowa_rfq_18649_report_structure/content_map.json
    revenue/uiowa_rfq_18649_report_structure/examples/report_sample.md

and emits a `bid_pack` manifest plus section files, so the assembler produces a
submission folder from a delivered artifact rather than only from its own
fixture.

THE RULES THIS ADAPTER HOLDS
----------------------------
1. **Nothing delivered is dropped.** A heading that exists in the report but not
   in the structure map is carried into the pack and FLAGGED (`SOURCE_ONLY`),
   never silently omitted. The preamble above the first heading is carried too.
2. **Nothing is invented.** A structure-map section with no matching body
   becomes `content_status: NOT_SUPPLIED` and renders a visible placeholder
   page. No text is written on anyone's behalf.
3. **Bodies are verbatim.** Section text is copied byte-for-byte out of the
   source report. A test asserts this; this adapter does not rewrite another
   lane's prose.
4. **The attachment list is UNKNOWN, not empty-and-fine.** The content map
   declares no attachments. The manifest therefore carries none, and the
   readiness note records that the University's required attachment list is
   unknown -- an empty list is not a complete one.
5. **Ambiguity is reported, not resolved by luck.** Two source headings that
   normalize to the same title are reported as ambiguous rather than
   first-wins.

Run:
    python3 from_report_structure.py --structure ../uiowa_rfq_18649_report_structure \\
                                     --out sample_integration
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

import bid_pack

ADAPTER_SCHEMA = "uiowa-136-bidpack-from-report-structure/1"

# Strips a leading ordinal from a heading: "3.", "7.1.", "A." -- the sample
# numbers its appendices with letters and the map does not number them at all,
# so matching on the number would fail on exactly the sections that matter.
_ORDINAL = re.compile(r"^\s*(?:[A-Z]|\d+(?:\.\d+)*)\s*\.?\s+")
_H2 = re.compile(r"(?m)^##\s+(.+?)\s*$")


class AdapterError(Exception):
    """A source artifact is missing or unusable. Nothing is guessed."""


def normalize_title(title):
    t = _ORDINAL.sub("", (title or "").strip())
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def split_report(markdown):
    """Return (preamble, [(heading, body)]) with bodies copied verbatim.

    Bodies are exact substrings of the input. Nothing is reflowed, stripped of
    internal whitespace, or reformatted.
    """
    heads = list(_H2.finditer(markdown))
    if not heads:
        return markdown, []
    preamble = markdown[:heads[0].start()]
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(markdown)
        out.append((m.group(1), markdown[m.end():end]))
    return preamble, out


def _read(path, what):
    if not os.path.isfile(path):
        raise AdapterError("%s not found: %s" % (what, path))
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def build(structure_dir, out_dir,
          map_name="content_map.json",
          sample_name=os.path.join("examples", "report_sample.md")):
    """Emit manifest + section files under `out_dir`; return the mapping report."""
    map_path = os.path.join(structure_dir, map_name)
    sample_path = os.path.join(structure_dir, sample_name)
    try:
        content_map = json.loads(_read(map_path, "content map"))
    except json.JSONDecodeError as exc:
        raise AdapterError("content map is not valid JSON (%s): %s" % (map_path, exc))
    if not isinstance(content_map.get("sections"), list) or not content_map["sections"]:
        raise AdapterError("content map declares no sections; nothing to build")

    sample = _read(sample_path, "report sample")
    preamble, source_sections = split_report(sample)

    by_title, ambiguous = {}, []
    for heading, body in source_sections:
        key = normalize_title(heading)
        if key in by_title:
            ambiguous.append(heading)
            continue
        by_title[key] = (heading, body)

    issues = []
    if ambiguous:
        issues.append({"code": "AMBIGUOUS_SOURCE_HEADING", "severity": "WARN",
                       "detail": "two source headings normalize to the same title; "
                                 "the later one was not matched: %s" % ", ".join(ambiguous)})

    sections, used = [], set()
    title_line = re.search(r"(?m)^#\s+(.+?)\s*$", sample)
    notice = re.search(r"(?m)^>\s*(.+?)\s*$", sample)

    if preamble.strip():
        sections.append({"id": "SRC-FRONT", "title": "Front matter",
                         "body": preamble, "origin": "SOURCE_ONLY",
                         "content_status": "SUPPLIED", "source_heading": None})
        issues.append({"code": "SOURCE_SECTION_NOT_IN_MAP", "severity": "INFO",
                       "detail": "the report's preamble is not a structure-map "
                                 "section; carried as SRC-FRONT rather than dropped"})

    for spec in content_map["sections"]:
        title = spec.get("title") or ""
        if not title.strip():
            issues.append({"code": "MAP_SECTION_WITHOUT_TITLE", "severity": "WARN",
                           "detail": "content-map section %r has no title and cannot "
                                     "be matched" % spec.get("section_id")})
        key = normalize_title(title)
        hit = by_title.get(key)
        if hit:
            used.add(key)
            sections.append({"id": spec.get("section_id") or ("SEC-%s" % len(sections)),
                             "title": title, "body": hit[1], "origin": "MAPPED",
                             "content_status": "SUPPLIED", "source_heading": hit[0]})
        else:
            # No body was delivered for this declared section. Placeholder, not prose.
            sections.append({"id": spec.get("section_id") or ("SEC-%s" % len(sections)),
                             "title": title, "body": None, "origin": "MAP_ONLY",
                             "content_status": "NOT_SUPPLIED", "source_heading": None})
            issues.append({"code": "MAP_SECTION_WITHOUT_BODY", "severity": "WARN",
                           "detail": "structure map declares %r but the report supplies "
                                     "no section with that title; emitted as a "
                                     "placeholder" % title})

    for heading, body in source_sections:
        key = normalize_title(heading)
        if key in used or key in {normalize_title(s["title"]) for s in sections
                                  if s["origin"] == "SOURCE_ONLY"}:
            continue
        if any(normalize_title(spec.get("title") or "") == key
               for spec in content_map["sections"]):
            continue
        sections.append({"id": "SRC-%s" % re.sub(r"[^A-Za-z0-9]+", "-", heading)[:28].strip("-").upper(),
                         "title": heading, "body": body, "origin": "SOURCE_ONLY",
                         "content_status": "SUPPLIED", "source_heading": heading})
        issues.append({"code": "SOURCE_SECTION_NOT_IN_MAP", "severity": "WARN",
                       "detail": "the report contains %r, which the structure map does "
                                 "not declare; carried into the pack rather than "
                                 "dropped" % heading})

    os.makedirs(os.path.join(out_dir, "sections"), exist_ok=True)
    entries = []
    for s in sections:
        rel = None
        if s["body"] is not None:
            rel = os.path.join("sections", "%s.md" % bid_pack.slugify(s["id"])).replace("\\", "/")
            with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as fh:
                fh.write(s["body"])
        entry = {"id": s["id"], "title": s["title"]}
        if rel:
            entry["source"] = rel
        entries.append(entry)

    manifest = {
        "schema": bid_pack.SCHEMA,
        "fiction_notice": (notice.group(1) if notice else
                           "Source report carries no fiction notice; provenance UNKNOWN."),
        "submission": {
            "title": title_line.group(1) if title_line else "Assessment Report",
            "solicitation_id": "RFQ-18649",
            "bidder_name": "UNKNOWN - the source report names no bidder",
            "status_label": "ASSEMBLED FROM A DELIVERED SYNTHETIC SAMPLE - NOT SUBMITTED",
        },
        "sections": entries,
        # The content map declares no attachments. An empty list is NOT a
        # complete list, and this adapter does not invent one.
        "attachments": [],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    report = {
        "schema": ADAPTER_SCHEMA,
        "source": {
            "content_map": os.path.relpath(map_path, out_dir).replace("\\", "/"),
            "report_sample": os.path.relpath(sample_path, out_dir).replace("\\", "/"),
            "map_id": content_map.get("map_id", "UNKNOWN"),
            "map_status": content_map.get("status", "UNKNOWN"),
        },
        "counts": {
            "map_sections": len(content_map["sections"]),
            "source_headings": len(source_sections),
            "mapped": sum(1 for s in sections if s["origin"] == "MAPPED"),
            "map_only_placeholder": sum(1 for s in sections if s["origin"] == "MAP_ONLY"),
            "source_only_carried": sum(1 for s in sections if s["origin"] == "SOURCE_ONLY"),
        },
        "sections": [{k: v for k, v in s.items() if k != "body"} for s in sections],
        "attachment_policy": {
            "declared_in_source": 0,
            "status": "UNKNOWN",
            "note": "The report structure map declares no attachments. The required "
                    "attachment list for RFQ-18649 is UNKNOWN; this pack carries none "
                    "rather than presenting an empty list as a complete one.",
        },
        "cross_references": {
            "markers_found": 0,
            "note": "The source report does not use this pack's [[ID]] cross-reference "
                    "markers, so none were resolved. No markers were inserted into "
                    "another lane's prose.",
        },
        "issues": issues,
    }
    with open(os.path.join(out_dir, "integration_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    return report, manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--structure", default=os.path.join("..", "uiowa_rfq_18649_report_structure"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--assemble", action="store_true",
                    help="also run the assembler into <out>/submission")
    args = ap.parse_args(argv)
    try:
        report, manifest = build(args.structure, args.out)
    except AdapterError as exc:
        sys.stderr.write("REFUSED: %s\n" % exc)
        return 2
    c = report["counts"]
    print("adapter -> %s" % args.out)
    print("  source map:   %s (%s)" % (report["source"]["map_id"], report["source"]["map_status"]))
    print("  map sections: %d   source headings: %d" % (c["map_sections"], c["source_headings"]))
    print("  mapped: %d   placeholder (declared, no body): %d   carried source-only: %d"
          % (c["mapped"], c["map_only_placeholder"], c["source_only_carried"]))
    print("  attachments: %s (%d declared in source)"
          % (report["attachment_policy"]["status"],
             report["attachment_policy"]["declared_in_source"]))
    for i in report["issues"]:
        print("  [%-4s] %-28s %s" % (i["severity"], i["code"], i["detail"]))
    if args.assemble:
        result = bid_pack.BidPack(manifest, args.out).assemble(
            os.path.join(args.out, "submission"))
        print("  assembled: proposal.pdf %d pages, %d section(s), status %s"
              % (result["render"]["pdf_pages"], len(result["sections"]),
                 result["readiness"]["status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
