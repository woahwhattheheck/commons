#!/usr/bin/env python3
"""Four-level traceability checker for a miniature assessment report bundle.

    statement (report prose) -> finding -> citation -> source record on disk

It fails loudly on an orphan at any level, in BOTH directions, and -- the part
that matters in a long engagement -- it compares what the report *asserts*
against what the record *says*, so a record edited after the report was written
breaks the build instead of quietly changing what the report means.

Why the agreement layer exists: link integrity and evidentiary agreement are
different properties. A bundle whose ids all resolve can still contain a
sentence that flatly contradicts the record it cites, because nothing ever
re-read the record. Over a long engagement the report is edited many times
after the findings are written, so drift -- not a typo'd id -- is the realistic
failure. See README "The failure this exists to catch".

Python 3 standard library only. No network. Deterministic: no clock, no RNG,
sorted traversal, so two operators get byte-identical output.
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema as S

FILES = ["sources.csv", "evidence.csv", "findings.csv", "recommendations.csv", "trace-map.csv"]
REPORTS = ["executive-summary.md", "final-report.md"]

CLAIM_RE = re.compile(r"^\*\*(S-\d{3})\.\*\*")
TAG_RE = re.compile(r"\[(F|E|R|LIMIT):([^\]]+)\]")
QUANT_RE = re.compile(r"^QUANTITY\s+(\S+?)=(\S+)(?:\s+(\S+))?\s*$", re.M)
ASSERT_RE = re.compile(r"^(E-\d{3})\.([A-Za-z0-9_]+)=(.+)$")


class Report:
    """Collects findings so one run reports everything, not just the first stop."""

    def __init__(self):
        self.items = []

    def add(self, rule, where, detail, level="error"):
        self.items.append({"rule": rule, "level": level, "where": where,
                           "detail": detail, "rule_text": S.RULES.get(rule, "")})

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "error"]

    @property
    def warnings(self):
        return [i for i in self.items if i["level"] == "warning"]

    def sorted_items(self):
        return sorted(self.items, key=lambda i: (i["rule"], i["where"]))


def _paragraphs(text):
    """Report paragraphs, with fenced code and headings removed.

    Headings are not claims, and a fenced block is a transcript rather than
    prose, so neither is held to the registered-or-narrative contract.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block or block.startswith("#") or set(block) <= set("-= "):
            continue
        out.append(block)
    return out


def read_bundle(root, rep):
    """Load every file; a missing file or column is a structural failure."""
    data = {}
    for name in FILES:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            rep.add("T001", name, "required file is not in %s" % root)
            data[name] = []
            continue
        try:
            rows, cols = S.load_csv(path)
        except (csv.Error, UnicodeDecodeError) as exc:
            rep.add("T001", name, "file could not be parsed as CSV: %s" % exc)
            data[name] = []
            continue
        missing = [c for c in S.REQUIRED_COLUMNS[name] if c not in cols]
        for c in missing:
            rep.add("T002", name, "column %r is absent" % c)
        data[name] = [] if missing else rows
    return data


def check_ids(data, rep):
    """Format and uniqueness. A duplicate id makes every downstream link a coin flip."""
    for name, key in (("sources.csv", "source_id"), ("evidence.csv", "evidence_id"),
                      ("findings.csv", "finding_id"),
                      ("recommendations.csv", "recommendation_id"),
                      ("trace-map.csv", "statement_id")):
        seen = set()
        for row in data[name]:
            val = (row.get(key) or "").strip()
            if not S.ID_PATTERNS[key].match(val):
                rep.add("T004", "%s:%s" % (name, val or "<blank>"),
                        "%r is not a valid %s" % (val, key))
            if val in seen:
                rep.add("T003", "%s:%s" % (name, val), "id appears more than once")
            seen.add(val)


def load_sources(root, data, rep):
    """Resolve every registered source to bytes on disk, then to its declared quantities."""
    sources = {}
    root_abs = os.path.realpath(root)
    for row in data["sources.csv"]:
        sid = row["source_id"].strip()
        rel = (row.get("path") or "").strip()
        full = os.path.realpath(os.path.join(root, rel))
        # A source register is operator-supplied text; it does not get to point
        # the checker outside the bundle.
        if not full.startswith(root_abs + os.sep):
            rep.add("T005", "sources.csv:%s" % sid, "path %r escapes the bundle" % rel)
            continue
        if not os.path.isfile(full):
            rep.add("T106", "sources.csv:%s" % sid, "no file at %r" % rel)
            continue
        with open(full, encoding="utf-8") as fh:
            body = fh.read()
        actual = S.file_sha256(full)
        declared = (row.get("sha256") or "").strip()
        if declared and declared != actual:
            rep.add("T107", "sources.csv:%s" % sid,
                    "record on disk has changed since it was registered "
                    "(registered %s..., on disk %s...)" % (declared[:12], actual[:12]))
        quants = {m.group(1): (m.group(2), m.group(3) or "")
                  for m in QUANT_RE.finditer(body)}
        sources[sid] = {"row": row, "body": body, "sha256": actual, "quantities": quants}
    return sources


def check_evidence(data, sources, rep):
    """Citation -> source record: the id resolves, the anchor resolves, the number resolves."""
    for row in data["evidence.csv"]:
        eid = row["evidence_id"].strip()
        sid = (row.get("source_id") or "").strip()
        if sid not in sources:
            rep.add("T105", "evidence.csv:%s" % eid,
                    "cites source %r which is not a resolvable source record" % sid)
            continue
        src = sources[sid]
        locator = (row.get("locator") or "").strip()
        # The anchor must be present in the bytes. Renaming a section in a
        # source silently detaches the citation from what it claimed to cite.
        if "[anchor: %s]" % locator not in src["body"]:
            rep.add("T108", "evidence.csv:%s" % eid,
                    "locator %r has no [anchor: ...] in %s" % (locator, sid))
        for qname, (qval, _unit) in sorted(S.parse_quantities(row.get("quantities")).items()):
            if qname not in src["quantities"]:
                rep.add("T109", "evidence.csv:%s" % eid,
                        "quantity %r is not declared by source %s" % (qname, sid))
            elif src["quantities"][qname][0] != qval:
                rep.add("T109", "evidence.csv:%s" % eid,
                        "quantity %s: evidence says %r, source %s says %r"
                        % (qname, qval, sid, src["quantities"][qname][0]))


def parse_reports(root, rep):
    """Every non-heading paragraph is a registered claim or explicitly narrative.

    T202 is the exact check. T201 is the net under it: marking a paragraph
    narrative must not be a way to slip an unsourced quantity or universal
    into a leadership summary.
    """
    claims, narratives = {}, []
    for name in REPORTS:
        path = os.path.join(root, name)
        if not os.path.exists(path):
            rep.add("T001", name, "required report file is not in the bundle")
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for para in _paragraphs(text):
            m = CLAIM_RE.match(para)
            if m:
                tags = {"F": set(), "E": set(), "R": set(), "LIMIT": set()}
                for kind, body in TAG_RE.findall(para):
                    tags[kind] |= {x.strip() for x in body.split(",") if x.strip()}
                body = TAG_RE.sub("", para[m.end():])
                claims.setdefault(m.group(1), []).append(
                    {"file": name, "text": body, "tags": tags,
                     "digest": S.paragraph_digest(body)})
            elif "{narrative}" in para:
                narratives.append((name, para))
                for marker in S.CLAIM_MARKERS:
                    hit = marker.search(para.replace("{narrative}", ""))
                    if hit:
                        rep.add("T201", name,
                                "paragraph marked {narrative} asserts %r: %s"
                                % (hit.group(0), S.norm(para)[:110]), "warning")
                        break
            else:
                rep.add("T202", name,
                        "unregistered, unmarked paragraph: %s" % S.norm(para)[:110])
    return claims


def check_statements(data, claims, findings, evidence, rec_ids, rep):
    """The agreement layer: does the prose still match the record it names?"""
    for row in data["trace-map.csv"]:
        stid = row["statement_id"].strip()
        where = "trace-map.csv:%s" % stid
        fids = S.split_ids(row.get("finding_ids"))
        eids = S.split_ids(row.get("evidence_ids"))
        rids = S.split_ids(row.get("recommendation_ids"))

        for fid in fids:
            if fid not in findings:
                rep.add("T101", where, "cites finding %r which does not exist" % fid)
        for rid in rids:
            if rid not in rec_ids:
                rep.add("T102", where, "cites recommendation %r which does not exist" % rid)
        for eid in eids:
            if eid not in evidence:
                rep.add("T103", where, "cites evidence %r which does not exist" % eid)

        paras = claims.get(stid, [])
        declared_files = {p.split("#")[0] for p in S.split_ids(row.get("report_location"))}
        found_files = {p["file"] for p in paras}
        for missing in sorted(declared_files - found_files):
            rep.add("T111", where, "declared in %s but no paragraph there carries it" % missing)
        if not paras:
            continue
        if len({p["digest"] for p in paras}) > 1:
            rep.add("T112", where,
                    "appears in %s with different wording in each"
                    % ", ".join(sorted(found_files)))
        prose = paras[0]
        if prose["tags"]["F"] != set(fids) or prose["tags"]["E"] != set(eids) \
                or prose["tags"]["R"] != set(rids):
            rep.add("T110", where,
                    "prose tags F=%s E=%s R=%s do not match the map"
                    % (sorted(prose["tags"]["F"]), sorted(prose["tags"]["E"]),
                       sorted(prose["tags"]["R"])))
        declared_sd = (row.get("statement_digest") or "").strip()
        if declared_sd and declared_sd != prose["digest"]:
            rep.add("T305", where,
                    "report wording changed after registration "
                    "(registered %s, now %s)" % (declared_sd, prose["digest"]))

        # -- polarity ---------------------------------------------------
        pol = (row.get("asserts_polarity") or "").strip()
        if pol and pol not in S.POLARITIES:
            rep.add("T301", where, "asserts_polarity %r is not a known polarity" % pol)
        for fid in fids:
            f = findings.get(fid)
            if not f:
                continue
            if pol and f["type"].strip() not in (pol, "mixed") and pol != "mixed":
                rep.add("T301", where,
                        "statement asserts %r but finding %s is recorded as %r"
                        % (pol, fid, f["type"].strip()))
            # -- drift ---------------------------------------------------
            # The digest covers exactly the fields a statement rests on, over
            # NORMALISED text, so re-quoting a CSV cell is not drift and
            # changing what a finding says is.
            declared = {}
            for part in S.split_ids(row.get("finding_digest")):
                if "=" in part:
                    k, v = part.split("=", 1)
                    declared[k.strip()] = v.strip()
            if fid in declared:
                actual_fd = S.record_digest(f)
                if actual_fd != declared[fid]:
                    rep.add("T306", where,
                            "finding %s changed after this statement was registered "
                            "(registered %s, now %s) -- re-read the report against it, "
                            "then re-register deliberately"
                            % (fid, declared[fid], actual_fd))
            if S.norm(f.get("limitation", "")) and (row.get("limitation_ack") or "").strip() != "yes":
                rep.add("T303", where,
                        "finding %s carries a limitation but the statement does not "
                        "acknowledge it" % fid)
            if S.norm(f.get("limitation", "")) and paras \
                    and ("LIMIT:%s" % fid) not in " ".join(
                        "[LIMIT:%s]" % x for p in paras for x in p["tags"]["LIMIT"]):
                rep.add("T303", where,
                        "finding %s carries a limitation that the report paragraph "
                        "does not mark" % fid)

        # -- quantity ---------------------------------------------------
        aq = (row.get("asserts_quantity") or "").strip()
        if aq:
            m = ASSERT_RE.match(aq)
            if not m:
                rep.add("T302", where, "asserts_quantity %r is not E-NNN.name=value" % aq)
                continue
            eid, qname, qval = m.group(1), m.group(2), m.group(3).strip()
            if eid not in evidence:
                rep.add("T302", where, "asserts a quantity on unknown evidence %r" % eid)
                continue
            have = S.parse_quantities(evidence[eid].get("quantities"))
            if qname not in have:
                rep.add("T302", where,
                        "evidence %s declares no quantity %r" % (eid, qname))
            elif have[qname][0] == S.UNKNOWN and qval != S.UNKNOWN:
                rep.add("T304", where,
                        "asserts %s=%s where %s records UNKNOWN -- an absent input "
                        "must not become a number" % (qname, qval, eid))
            elif have[qname][0] != qval:
                rep.add("T302", where,
                        "asserts %s=%s but %s records %s"
                        % (qname, qval, eid, have[qname][0]))


def check_reverse(data, claims, findings, evidence, sources, rep):
    """Nothing registered may go unused, and nothing used may go unregistered."""
    cited_f, cited_e, cited_r = set(), set(), set()
    for row in data["trace-map.csv"]:
        cited_f |= set(S.split_ids(row.get("finding_ids")))
        cited_e |= set(S.split_ids(row.get("evidence_ids")))
        cited_r |= set(S.split_ids(row.get("recommendation_ids")))
    f_evidence = set()
    for row in data["findings.csv"]:
        f_evidence |= set(S.split_ids(row.get("evidence_ids")))
    e_sources = {(r.get("source_id") or "").strip() for r in data["evidence.csv"]}

    for fid in sorted(findings):
        if fid not in cited_f:
            rep.add("T203", "findings.csv:%s" % fid,
                    "finding reaches no report statement", "warning")
    for eid in sorted(evidence):
        if eid not in f_evidence:
            rep.add("T204", "evidence.csv:%s" % eid,
                    "evidence is cited by no finding", "warning")
    for sid in sorted(sources):
        if sid not in e_sources:
            rep.add("T205", "sources.csv:%s" % sid,
                    "source is cited by no evidence", "warning")
    for row in data["recommendations.csv"]:
        rid = row["recommendation_id"].strip()
        if rid not in cited_r:
            rep.add("T206", "recommendations.csv:%s" % rid,
                    "recommendation reaches no report statement", "warning")
        linked = S.split_ids(row.get("linked_findings"))
        for fid in linked:
            if fid not in findings:
                rep.add("T104", "recommendations.csv:%s" % rid,
                        "links finding %r which does not exist" % fid)
        types = {findings[f]["type"].strip() for f in linked if f in findings}
        if types and types <= {"strength"}:
            rep.add("T307", "recommendations.csv:%s" % rid,
                    "rests only on findings recorded as strengths -- either the "
                    "finding moved or the recommendation lost its basis")
    # Statements present in prose but never registered in the map.
    registered = {r["statement_id"].strip() for r in data["trace-map.csv"]}
    for stid in sorted(set(claims) - registered):
        rep.add("T202", "report:%s" % stid,
                "paragraph carries statement id %s which is in no trace map row" % stid)


def check(root):
    rep = Report()
    data = read_bundle(root, rep)
    check_ids(data, rep)
    findings = {r["finding_id"].strip(): r for r in data["findings.csv"]}
    evidence = {r["evidence_id"].strip(): r for r in data["evidence.csv"]}
    rec_ids = {r["recommendation_id"].strip() for r in data["recommendations.csv"]}
    for row in data["findings.csv"]:
        if row["type"].strip() not in S.FINDING_TYPES:
            rep.add("T004", "findings.csv:%s" % row["finding_id"],
                    "type %r is not a known finding type" % row["type"])
        for eid in S.split_ids(row.get("evidence_ids")):
            if eid not in evidence:
                rep.add("T103", "findings.csv:%s" % row["finding_id"],
                        "cites evidence %r which does not exist" % eid)
    sources = load_sources(root, data, rep)
    check_evidence(data, sources, rep)
    claims = parse_reports(root, rep)
    check_statements(data, claims, findings, evidence, rec_ids, rep)
    check_reverse(data, claims, findings, evidence, sources, rep)
    return rep, data, findings, evidence, sources, claims


def trace_map(data, findings, evidence, sources):
    """The deliverable: statement -> finding -> citation -> source file, generated."""
    rows = []
    for st in sorted(data["trace-map.csv"], key=lambda r: r["statement_id"]):
        for fid in S.split_ids(st.get("finding_ids")) or ["-"]:
            f = findings.get(fid, {})
            for eid in S.split_ids(f.get("evidence_ids", "")) or ["-"]:
                e = evidence.get(eid, {})
                sid = (e.get("source_id") or "-").strip()
                rows.append({
                    "statement_id": st["statement_id"],
                    "report_location": st.get("report_location", ""),
                    "finding_id": fid,
                    "finding_type": f.get("type", ""),
                    "evidence_id": eid,
                    "locator": e.get("locator", ""),
                    "source_id": sid,
                    "source_path": sources.get(sid, {}).get("row", {}).get("path", ""),
                    "source_sha256": sources.get(sid, {}).get("sha256", "")[:16],
                })
    return rows


def register(root):
    """Recompute the digests a statement is bound to. Deliberate, never automatic.

    Drift must not be self-healing: if editing a record silently refreshed the
    digest, the checker would pass forever and the guarantee would be theatre.
    The operator runs this on purpose, and it prints exactly what moved.
    """
    rep = Report()
    data = read_bundle(root, rep)
    findings = {r["finding_id"].strip(): r for r in data["findings.csv"]}
    claims = parse_reports(root, Report())
    path = os.path.join(root, "trace-map.csv")
    rows, cols = S.load_csv(path)
    changed = []
    for row in rows:
        fids = S.split_ids(row.get("finding_ids"))
        new_fd = ";".join("%s=%s" % (f, S.record_digest(findings[f]))
                          for f in fids if f in findings)
        paras = claims.get(row["statement_id"].strip(), [])
        new_sd = paras[0]["digest"] if paras else ""
        for key, new in (("finding_digest", new_fd), ("statement_digest", new_sd)):
            if (row.get(key) or "") != new:
                changed.append("%s %s: %s -> %s" % (row["statement_id"], key,
                                                    row.get(key) or "<blank>", new or "<blank>"))
                row[key] = new
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("registered %d statement(s); %d digest value(s) changed" % (len(rows), len(changed)))
    for line in changed:
        print("  " + line)
    return 0


def seal(root):
    """Record the sha256 of each source record. Separate from --register on purpose.

    Sealing a source and binding a statement to a finding are different acts of
    authorship. Folding them into one command would let "my report changed" and
    "my evidence changed" be approved by the same keystroke.
    """
    path = os.path.join(root, "sources.csv")
    rows, cols = S.load_csv(path)
    changed = []
    for row in rows:
        full = os.path.join(root, (row.get("path") or "").strip())
        if not os.path.isfile(full):
            print("  MISSING %s -> %s" % (row["source_id"], row.get("path")))
            continue
        actual = S.file_sha256(full)
        if (row.get("sha256") or "") != actual:
            changed.append("%s: %s -> %s" % (row["source_id"],
                                             (row.get("sha256") or "<blank>")[:12], actual[:12]))
            row["sha256"] = actual
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("sealed %d source record(s); %d digest value(s) changed" % (len(rows), len(changed)))
    for line in changed:
        print("  " + line)
    return 0


def render_text(rep, data, rows):
    out = []
    out.append("bundle: sources=%d evidence=%d findings=%d recommendations=%d statements=%d"
               % (len(data["sources.csv"]), len(data["evidence.csv"]),
                  len(data["findings.csv"]), len(data["recommendations.csv"]),
                  len(data["trace-map.csv"])))
    out.append("trace rows (statement -> finding -> citation -> source): %d" % len(rows))
    if not rep.items:
        out.append("")
        out.append("TRACE CHECK: PASS - every statement resolves to a finding, every")
        out.append("finding to a citation, every citation to a source record on disk,")
        out.append("and every asserted polarity and quantity matches its record.")
        return "\n".join(out)
    out.append("")
    for item in rep.sorted_items():
        out.append("%-7s %-5s %-28s %s" % (item["level"].upper(), item["rule"],
                                           item["where"], item["detail"]))
    out.append("")
    out.append("TRACE CHECK: FAIL - %d error(s), %d warning(s)"
               % (len(rep.errors), len(rep.warnings)))
    return "\n".join(out)


def render_markdown(rep, data, rows):
    out = ["# Finding-to-source trace map (generated)", "",
           "Synthetic rehearsal bundle. Not a University of Iowa finding.", "",
           "| statement | finding | type | citation | locator | source | sha256 |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %s | %s | `%s` |" % (
            r["statement_id"], r["finding_id"], r["finding_type"], r["evidence_id"],
            r["locator"], r["source_path"], r["source_sha256"]))
    out += ["", "## Check result", ""]
    if not rep.items:
        out.append("**PASS** - no orphan at any level; every asserted polarity and "
                   "quantity agrees with its record.")
    else:
        out += ["| level | rule | where | detail |", "|---|---|---|---|"]
        for i in rep.sorted_items():
            out.append("| %s | %s | %s | %s |" % (i["level"], i["rule"], i["where"],
                                                  i["detail"].replace("|", "\\|")))
        out += ["", "**FAIL** - %d error(s), %d warning(s)."
                % (len(rep.errors), len(rep.warnings))]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle", help="path to the bundle directory")
    ap.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    ap.add_argument("--register", action="store_true",
                    help="recompute statement/finding digests after a deliberate edit")
    ap.add_argument("--seal", action="store_true",
                    help="record the sha256 of each source record (deliberate)")
    ap.add_argument("--rules", action="store_true", help="print the rule catalogue and exit")
    args = ap.parse_args(argv)
    if args.rules:
        for rule in sorted(S.RULES):
            print("%-6s %s" % (rule, S.RULES[rule]))
        return 0
    if not os.path.isdir(args.bundle):
        print("no such bundle directory: %s" % args.bundle, file=sys.stderr)
        return 2
    if args.seal:
        return seal(args.bundle)
    if args.register:
        return register(args.bundle)
    rep, data, findings, evidence, sources, _claims = check(args.bundle)
    rows = trace_map(data, findings, evidence, sources)
    if args.format == "json":
        print(json.dumps({"bundle": os.path.basename(os.path.abspath(args.bundle)),
                          "counts": {"sources": len(data["sources.csv"]),
                                     "evidence": len(data["evidence.csv"]),
                                     "findings": len(data["findings.csv"]),
                                     "recommendations": len(data["recommendations.csv"]),
                                     "statements": len(data["trace-map.csv"]),
                                     "trace_rows": len(rows)},
                          "result": "PASS" if not rep.errors else "FAIL",
                          "errors": len(rep.errors), "warnings": len(rep.warnings),
                          "items": rep.sorted_items(), "trace_map": rows},
                         indent=2, sort_keys=True))
    elif args.format == "markdown":
        print(render_markdown(rep, data, rows))
    else:
        print(render_text(rep, data, rows))
    return 1 if rep.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
