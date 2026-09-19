"""UIOWA-136 -- bidder attachment assembly and navigation tool.

Turns a manifest of prepared proposal components into an orderly submission
folder: stable filenames, an attachment index, section/page cross-references,
and document navigation (PDF outline + internal links, DOCX bookmarks +
heading-level nav).

THE ONE RULE THIS TOOL EXISTS TO ENFORCE
----------------------------------------
A declared attachment that is not on disk becomes a VISIBLE PLACEHOLDER ROW in
the index. It is never dropped (which makes an incomplete pack look complete)
and never substituted with invented content (which makes it look supplied).
The filesystem is the ground truth: a manifest that says `"provided": true` for
a file that does not exist LOSES to the filesystem and is reported as a
contradiction. Size, digest and page number for an absent file stay UNKNOWN --
never 0, never "n/a", never a score.

There is no readiness percentage and no maturity rating anywhere in the output.
The readiness block reports counts and names: how many required attachments
were declared, which ones are present, which ones are not. A count of observed
facts is not a rating.

Run:
    python3 bid_pack.py --manifest fixtures/manifest.json --out sample_output
    python3 bid_pack.py --manifest fixtures/manifest.json --out /tmp/x --strict
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys

import docxwrite
import pdfwrite

SCHEMA = "uiowa-136-bid-pack/1"
MAX_PAGINATION_PASSES = 8

REQUIRED_TOP_KEYS = ("schema", "submission", "sections", "attachments")
REQUIRED_SECTION_KEYS = ("id", "title")
REQUIRED_ATTACHMENT_KEYS = ("id", "title", "category")

# Severities: ERROR blocks a truthful submission, WARN is a real gap the reader
# must see, INFO is a decision the assembler made and is disclosing.
ERROR, WARN, INFO = "ERROR", "WARN", "INFO"

REF_RE = re.compile(r"\[\[([A-Za-z0-9_.\-]+)\]\]")


class ManifestError(Exception):
    """The manifest cannot be assembled without inventing something."""


class PaginationError(Exception):
    """Page numbers did not settle, so no page number is trustworthy."""


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------

def slugify(text, limit=48):
    s = re.sub(r"[^0-9A-Za-z]+", "-", (text or "")).strip("-").lower()
    s = re.sub(r"-{2,}", "-", s)
    return (s[:limit].strip("-")) or "untitled"


def load_manifest(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise ManifestError("manifest not found: %s" % path)
    except json.JSONDecodeError as exc:
        raise ManifestError("manifest is not valid JSON (%s): %s" % (path, exc))
    validate_manifest(data)
    return data


def validate_manifest(data):
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    missing = [k for k in REQUIRED_TOP_KEYS if k not in data]
    if missing:
        raise ManifestError("manifest is missing required key(s): %s"
                            % ", ".join(sorted(missing)))
    if data.get("schema") != SCHEMA:
        raise ManifestError("unsupported manifest schema %r (expected %r)"
                            % (data.get("schema"), SCHEMA))
    for name, items, keys in (("sections", data["sections"], REQUIRED_SECTION_KEYS),
                              ("attachments", data["attachments"], REQUIRED_ATTACHMENT_KEYS)):
        if not isinstance(items, list):
            raise ManifestError("%s must be a list" % name)
        seen = set()
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                raise ManifestError("%s[%d] must be an object" % (name, i))
            gone = [k for k in keys if not item.get(k)]
            if gone:
                raise ManifestError("%s[%d] is missing required field(s): %s"
                                    % (name, i, ", ".join(gone)))
            if item["id"] in seen:
                raise ManifestError("duplicate id %r in %s" % (item["id"], name))
            seen.add(item["id"])
    if not data["sections"]:
        raise ManifestError("manifest declares no sections; there is nothing to assemble")


def _safe_join(root, rel):
    """Resolve `rel` under `root`, refusing anything that escapes the pack."""
    if os.path.isabs(rel):
        raise ManifestError("source path must be relative to the pack root: %r" % rel)
    full = os.path.normpath(os.path.join(root, rel))
    if not (full == root or full.startswith(root + os.sep)):
        raise ManifestError("source path escapes the pack root: %r" % rel)
    return full


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def _section_row(section, page_map):
    """Public view of a section: everything but the body, plus its 1-based page."""
    row = {k: v for k, v in section.items() if k != "body"}
    # A section that never got laid out has NO page number. Not page 0, not "-".
    row["page"] = page_map[section["id"]] + 1 if section["id"] in page_map else None
    return row


class BidPack(object):
    def __init__(self, manifest, root):
        self.m = manifest
        self.root = os.path.abspath(root)
        self.issues = []

    def _issue(self, severity, code, detail, ref=None):
        self.issues.append({"severity": severity, "code": code,
                            "detail": detail, "ref": ref})

    # -- filenames ---------------------------------------------------------

    def _assign_filenames(self):
        """Stable, sortable, collision-safe filenames.

        Collision detection is CASE-INSENSITIVE on purpose: a pack that is fine
        on Linux and silently overwrites a file on the reviewer's Windows or
        macOS machine is the exact failure this order is about.
        """
        taken = {}
        explicit = {}
        out = {}
        for prefix, items in (("", self.m["sections"]), ("A", self.m["attachments"])):
            for i, item in enumerate(items, start=1):
                ext = item.get("ext")
                if not ext:
                    src = item.get("source") or ""
                    ext = os.path.splitext(src)[1] or (".md" if prefix == "" else ".txt")
                if item.get("filename"):
                    name = item["filename"]
                    key = name.lower()
                    if key in explicit:
                        raise ManifestError(
                            "two entries declare the same filename %r (%s and %s); "
                            "one would overwrite the other on a case-insensitive "
                            "filesystem" % (name, explicit[key], item["id"]))
                    explicit[key] = item["id"]
                else:
                    name = "%s%02d-%s%s" % (prefix, i, slugify(item["title"]), ext)
                key = name.lower()
                if key in taken:
                    base, e = os.path.splitext(name)
                    name = "%s--%s%s" % (base, slugify(item["id"]), e)
                    self._issue(INFO, "FILENAME_COLLISION_RESOLVED",
                                "filename collided with %s (case-insensitively); "
                                "disambiguated to %r" % (taken[key], name), item["id"])
                    key = name.lower()
                taken[key] = item["id"]
                out[item["id"]] = name
        return out

    # -- inputs ------------------------------------------------------------

    def _load_sections(self, names):
        out = []
        for i, sec in enumerate(self.m["sections"], start=1):
            body, status = "", "SUPPLIED"
            src = sec.get("source")
            if not src:
                status = "NOT_SUPPLIED"
                self._issue(WARN, "SECTION_CONTENT_NOT_SUPPLIED",
                            "section %s (%s) declares no source file" % (sec["id"], sec["title"]),
                            sec["id"])
            else:
                path = _safe_join(self.root, src)
                if not os.path.isfile(path):
                    status = "NOT_SUPPLIED"
                    self._issue(WARN, "SECTION_CONTENT_NOT_SUPPLIED",
                                "section %s declares source %r which does not exist"
                                % (sec["id"], src), sec["id"])
                else:
                    with open(path, "r", encoding="utf-8") as fh:
                        body = fh.read()
            out.append({"id": sec["id"], "ordinal": i, "title": sec["title"],
                        "filename": names[sec["id"]], "content_status": status,
                        "body": body, "source": src})
        return out

    def _load_attachments(self, names):
        out = []
        for i, att in enumerate(self.m["attachments"], start=1):
            src = att.get("source")
            declared = bool(att.get("provided"))
            path = _safe_join(self.root, src) if src else None
            present = bool(path and os.path.isfile(path))
            size = sha = None
            if present:
                with open(path, "rb") as fh:
                    blob = fh.read()
                size = len(blob)
                sha = hashlib.sha256(blob).hexdigest()
                status = "SUPPLIED"
                if size == 0:
                    status = "SUPPLIED-EMPTY FILE"
                    self._issue(WARN, "ATTACHMENT_EMPTY_FILE",
                                "attachment %s is present but zero bytes; an empty file "
                                "is not evidence" % att["id"], att["id"])
                if not declared:
                    self._issue(INFO, "ATTACHMENT_PRESENT_NOT_DECLARED",
                                "attachment %s has a file on disk but the manifest does "
                                "not mark it provided; the file wins" % att["id"], att["id"])
            else:
                status = "PLACEHOLDER-NOT SUPPLIED"
                if declared:
                    # The manifest asserts a document that is not there. That is a
                    # false claim of supply, not a missing file, and it is an ERROR.
                    self._issue(ERROR, "ATTACHMENT_DECLARED_PROVIDED_BUT_ABSENT",
                                "attachment %s is marked provided=true but %r is not on "
                                "disk; reported as NOT SUPPLIED" % (att["id"], src or "(no source)"),
                                att["id"])
                sev = WARN if att.get("required") else INFO
                self._issue(sev, "ATTACHMENT_NOT_SUPPLIED",
                            "%s attachment %s (%s) is declared but no file was supplied; "
                            "emitted as a placeholder"
                            % ("required" if att.get("required") else "optional",
                               att["id"], att["title"]), att["id"])
            out.append({
                "id": att["id"], "ordinal": i, "title": att["title"],
                "category": att.get("category", "UNKNOWN"),
                "required": bool(att.get("required")),
                "status": status, "present": present,
                "filename": names[att["id"]] if present else None,
                "bytes": size, "sha256": sha, "source": src,
                "note": att.get("note", ""),
            })
        return out

    # -- cross references --------------------------------------------------

    def _resolve(self, text, sections, attachments, page_map, owner):
        """Replace [[ID]] markers with resolved prose; collect the references.

        An id that does not exist is NOT deleted and NOT invented: the prose
        keeps a loud [UNRESOLVED REFERENCE: id] marker and the reference is
        recorded as unresolved.
        """
        secs = {s["id"]: s for s in sections}
        atts = {a["id"]: a for a in attachments}
        refs = []

        def page_of(anchor):
            p = page_map.get(anchor)
            return str(p + 1) if p is not None else "--"

        def repl(match):
            rid = match.group(1)
            if rid in secs:
                s = secs[rid]
                refs.append({"from": owner, "to": rid, "kind": "section",
                             "status": "RESOLVED", "label": s["title"]})
                return "Section %d (%s), page %s" % (s["ordinal"], s["title"], page_of(rid))
            if rid in atts:
                a = atts[rid]
                state = "" if a["present"] else " - PLACEHOLDER, NOT SUPPLIED"
                refs.append({"from": owner, "to": rid, "kind": "attachment",
                             "status": "RESOLVED", "label": a["title"]})
                return ("Attachment %s (%s)%s - see attachment index, page %s"
                        % (rid, a["title"], state, page_of("IDX-" + rid)))
            refs.append({"from": owner, "to": rid, "kind": "unknown",
                         "status": "UNRESOLVED", "label": None})
            return "[UNRESOLVED REFERENCE: %s]" % rid

        return REF_RE.sub(repl, text), refs

    # -- document blocks ---------------------------------------------------

    def _blocks(self, sections, attachments, page_map):
        sub = self.m["submission"]
        all_refs = []
        b = [{"kind": "title", "text": sub.get("title") or "Proposal", "anchor": "DOC-TOP"}]
        for line in (
            "Solicitation: %s" % sub.get("solicitation_id", "UNKNOWN"),
            "Bidder: %s" % sub.get("bidder_name", "UNKNOWN"),
            "Submission status: %s" % sub.get("status_label", "UNKNOWN"),
            "Assembled by: bid_pack.py (%s)" % SCHEMA,
        ):
            b.append({"kind": "body", "text": line})
        if self.m.get("fiction_notice"):
            b.append({"kind": "spacer", "height": 10})
            b.append({"kind": "body", "text": self.m["fiction_notice"]})

        b.append({"kind": "pagebreak"})
        b.append({"kind": "heading", "text": "Document Map",
                  "anchor": "TOC", "outline": "Document Map"})
        b.append({"kind": "body", "text":
                  "Every row below is a live link in the PDF and a bookmark in the .docx."})
        b.append({"kind": "spacer", "height": 6})
        for s in sections:
            page = page_map.get(s["id"])
            pg = str(page + 1) if page is not None else "--"
            dots = "." * max(3, 62 - len(s["title"]))
            flag = "" if s["content_status"] == "SUPPLIED" else "  [CONTENT NOT SUPPLIED]"
            b.append({"kind": "mono",
                      "text": "%2d  %s %s %4s%s" % (s["ordinal"], s["title"], dots, pg, flag),
                      "dest": s["id"]})

        b.append({"kind": "spacer", "height": 12})
        b.append({"kind": "heading", "text": "Attachment Index",
                  "anchor": "ATTIDX", "outline": "Attachment Index"})
        b.append({"kind": "body", "text":
                  "UNKNOWN means no file was supplied, so size and digest could not be "
                  "measured. It is not zero and it is not a pass."})
        b.append({"kind": "spacer", "height": 6})
        b.append({"kind": "mono", "text":
                  "%-12s %-26s %-10s %-16s" % ("ID", "STATUS", "BYTES", "SHA256[:16]")})
        b.append({"kind": "mono", "text": "-" * 66})
        for a in attachments:
            size = "UNKNOWN" if a["bytes"] is None else "{:,}".format(a["bytes"])
            sha = a["sha256"][:16] if a["sha256"] else "UNKNOWN"
            b.append({"kind": "mono",
                      "text": "%-12s %-26s %-10s %-16s" % (a["id"], a["status"], size, sha),
                      "anchor": "IDX-" + a["id"]})
            tail = a["filename"] if a["present"] else "(no file supplied)"
            req = "required" if a["required"] else "optional"
            b.append({"kind": "mono",
                      "text": "             %s [%s, %s] -> %s"
                              % (a["title"], a["category"], req, tail)})

        ready = self._readiness(attachments)
        b.append({"kind": "spacer", "height": 12})
        b.append({"kind": "subheading", "text": "Submission completeness"})
        b.append({"kind": "body", "text": "Status: %s" % ready["status"]})
        b.append({"kind": "body", "text":
                  "Required attachments declared: %d. Present: %d. Not supplied: %d."
                  % (ready["required_declared"], ready["required_present"],
                     len(ready["required_not_supplied"]))})
        if ready["required_not_supplied"]:
            b.append({"kind": "body", "text": "Not supplied: %s"
                      % ", ".join(ready["required_not_supplied"])})

        for s in sections:
            b.append({"kind": "pagebreak"})
            b.append({"kind": "heading",
                      "text": "%d. %s" % (s["ordinal"], s["title"]),
                      "anchor": s["id"], "outline": "%d. %s" % (s["ordinal"], s["title"])})
            if s["content_status"] != "SUPPLIED":
                b.append({"kind": "body", "text":
                          "[SECTION CONTENT NOT SUPPLIED - this page is a placeholder. "
                          "No text was written on the bidder's behalf.]"})
                continue
            resolved, refs = self._resolve(s["body"], sections, attachments,
                                           page_map, s["id"])
            all_refs.extend(refs)
            for para in [p.strip() for p in resolved.split("\n\n") if p.strip()]:
                b.append({"kind": "body", "text": " ".join(para.split())})
                b.append({"kind": "spacer", "height": 6})
            mine = [r for r in refs]
            if mine:
                b.append({"kind": "spacer", "height": 8})
                b.append({"kind": "subheading", "text": "Cross-references"})
                for r in mine:
                    if r["status"] == "RESOLVED":
                        b.append({"kind": "link",
                                  "text": "-> %s: %s" % (r["to"], r["label"]),
                                  "dest": r["to"] if r["kind"] == "section" else "IDX-" + r["to"]})
                    else:
                        b.append({"kind": "body",
                                  "text": "-> %s: UNRESOLVED - no destination exists in "
                                          "this pack" % r["to"]})
        return b, all_refs

    def _readiness(self, attachments):
        req = [a for a in attachments if a["required"]]
        present = [a for a in req if a["present"] and a["bytes"]]
        missing = [a["id"] for a in req if not (a["present"] and a["bytes"])]
        return {
            "required_declared": len(req),
            "required_present": len(present),
            "required_not_supplied": missing,
            "status": "SUBMISSION_INCOMPLETE" if missing else "ALL_DECLARED_REQUIRED_ATTACHMENTS_PRESENT",
            "note": ("Counts describe declared-vs-present documents in this pack only. "
                     "Whether this list of attachments is the list the University "
                     "actually requires is UNKNOWN."),
        }

    # -- the run -----------------------------------------------------------

    def assemble(self, out_dir, write_files=True):
        names = self._assign_filenames()
        sections = self._load_sections(names)
        attachments = self._load_attachments(names)

        # Fixed-point pagination: resolved cross-reference prose contains page
        # numbers, and page numbers depend on how that prose wraps. Iterate
        # until the map stops moving. If it never settles, refuse -- an
        # unsettled page number is a wrong page number.
        page_map, passes = {}, 0
        blocks = None
        for passes in range(1, MAX_PAGINATION_PASSES + 1):
            blocks, refs = self._blocks(sections, attachments, page_map)
            pages = pdfwrite.paginate(blocks)
            new_map = {k: v[0] for k, v in pdfwrite.anchor_pages(pages).items()}
            if new_map == page_map:
                break
            page_map = new_map
        else:
            raise PaginationError(
                "page numbers did not settle after %d passes; refusing to print a "
                "page number that may be wrong" % MAX_PAGINATION_PASSES)

        for r in refs:
            if r["status"] == "UNRESOLVED":
                self._issue(WARN, "XREF_UNRESOLVED",
                            "section %s references %r, which is not a section or an "
                            "attachment in this pack" % (r["from"], r["to"]), r["from"])

        sub = self.m["submission"]
        title = sub.get("title") or "Proposal"
        author = sub.get("bidder_name", "")
        pdf_bytes, lost = pdfwrite.write_pdf(pages, title=title, author=author)
        if lost:
            self._issue(WARN, "UNICODE_NOT_REPRESENTABLE_IN_PDF",
                        "%d character(s) outside WinAnsi were replaced with '?' in the "
                        "PDF: %s (the .md and .docx outputs keep them)"
                        % (len(lost), " ".join(sorted(set(lost)))))

        result = {
            "schema": SCHEMA,
            "submission": sub,
            "fiction_notice": self.m.get("fiction_notice", ""),
            "sections": [_section_row(s, page_map) for s in sections],
            "attachments": [dict(a, index_page=(page_map["IDX-" + a["id"]] + 1
                                                if "IDX-" + a["id"] in page_map else None))
                            for a in attachments],
            "cross_references": refs,
            "readiness": self._readiness(attachments),
            "issues": self.issues,
            "render": {"pdf_pages": len(pages), "pagination_passes": passes,
                       "pdf_bytes": len(pdf_bytes)},
        }

        if write_files:
            self._write(out_dir, sections, attachments, blocks, pdf_bytes, result, title, author)
        return result

    def _write(self, out_dir, sections, attachments, blocks, pdf_bytes, result, title, author):
        os.makedirs(out_dir, exist_ok=True)
        docs = os.path.join(out_dir, "documents")
        atts = os.path.join(out_dir, "attachments")
        os.makedirs(docs, exist_ok=True)
        os.makedirs(atts, exist_ok=True)

        for s in sections:
            dest = os.path.join(docs, s["filename"])
            if s["content_status"] == "SUPPLIED":
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write("<!-- %s -->\n# %d. %s\n\n%s\n"
                             % (self.m.get("fiction_notice", ""), s["ordinal"],
                                s["title"], s["body"]))
            else:
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write("# %d. %s\n\nSECTION CONTENT NOT SUPPLIED. This file is a "
                             "placeholder so the gap is visible in the folder listing. "
                             "No text was written on the bidder's behalf.\n"
                             % (s["ordinal"], s["title"]))
        for a in attachments:
            if a["present"]:
                shutil.copyfile(_safe_join(self.root, a["source"]),
                                os.path.join(atts, a["filename"]))
            else:
                ph = os.path.join(atts, "A%02d-%s.PLACEHOLDER.txt" % (a["ordinal"], slugify(a["title"])))
                with open(ph, "w", encoding="utf-8") as fh:
                    fh.write("PLACEHOLDER - NOT SUPPLIED\n\nAttachment id: %s\nTitle: %s\n"
                             "Category: %s\nRequired: %s\n\nNo document was supplied for "
                             "this attachment. Size and digest are UNKNOWN. This file "
                             "exists so the absence is visible in the submission folder; "
                             "it is not the attachment and must not be submitted in its "
                             "place.\n" % (a["id"], a["title"], a["category"],
                                           "yes" if a["required"] else "no"))

        with open(os.path.join(out_dir, "proposal.pdf"), "wb") as fh:
            fh.write(pdf_bytes)
        docxwrite.write_docx(os.path.join(out_dir, "proposal.docx"), blocks,
                             title=title, author=author)

        with open(os.path.join(out_dir, "attachment_index.csv"), "w",
                  encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["attachment_id", "title", "category", "required", "status",
                        "filename", "bytes", "sha256", "index_page"])
            for a in result["attachments"]:
                w.writerow([a["id"], a["title"], a["category"],
                            "yes" if a["required"] else "no", a["status"],
                            a["filename"] or "UNKNOWN",
                            "UNKNOWN" if a["bytes"] is None else a["bytes"],
                            a["sha256"] or "UNKNOWN",
                            a["index_page"] if a["index_page"] else "UNKNOWN"])

        payload = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with open(os.path.join(out_dir, "bid_pack.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(result, content_digest=digest), indent=2,
                                sort_keys=True, ensure_ascii=False))

        with open(os.path.join(out_dir, "00-INDEX.md"), "w", encoding="utf-8") as fh:
            fh.write(self._index_md(result))

    def _index_md(self, result):
        r = result["readiness"]
        out = ["# Submission folder index", "",
               "> %s" % (result["fiction_notice"] or "(no fiction notice declared)"), "",
               "Solicitation: `%s`  " % result["submission"].get("solicitation_id", "UNKNOWN"),
               "Bidder: %s  " % result["submission"].get("bidder_name", "UNKNOWN"),
               "Submission status: **%s**  " % result["submission"].get("status_label", "UNKNOWN"),
               "Rendered proposal: `proposal.pdf` (%d pages), `proposal.docx`"
               % result["render"]["pdf_pages"], "",
               "## Documents", "",
               "| # | Section | File | PDF page | Content |",
               "|---|---|---|---|---|"]
        for s in result["sections"]:
            out.append("| %d | %s | `documents/%s` | %s | %s |"
                       % (s["ordinal"], s["title"], s["filename"],
                          s["page"] or "UNKNOWN", s["content_status"]))
        out += ["", "## Attachment index", "",
                "`UNKNOWN` = no file supplied, so nothing could be measured. Not zero.", "",
                "| ID | Title | Category | Required | Status | File | Bytes | SHA256 | Index page |",
                "|---|---|---|---|---|---|---|---|---|"]
        for a in result["attachments"]:
            out.append("| %s | %s | %s | %s | **%s** | %s | %s | %s | %s |"
                       % (a["id"], a["title"], a["category"],
                          "yes" if a["required"] else "no", a["status"],
                          "`attachments/%s`" % a["filename"] if a["filename"] else "_(none)_",
                          "UNKNOWN" if a["bytes"] is None else "{:,}".format(a["bytes"]),
                          "`%s`" % a["sha256"][:16] if a["sha256"] else "UNKNOWN",
                          a["index_page"] or "UNKNOWN"))
        out += ["", "## Submission completeness", "",
                "**%s**" % r["status"], "",
                "- Required attachments declared: %d" % r["required_declared"],
                "- Present: %d" % r["required_present"],
                "- Not supplied: %s" % (", ".join("`%s`" % i for i in r["required_not_supplied"]) or "none"),
                "", "> %s" % r["note"], "",
                "## Cross-references", ""]
        for x in result["cross_references"]:
            out.append("- `%s` -> `%s` (%s) **%s**" % (x["from"], x["to"], x["kind"], x["status"]))
        out += ["", "## Assembler issues", ""]
        if not result["issues"]:
            out.append("_none_")
        for i in result["issues"]:
            out.append("- **%s** `%s` %s" % (i["severity"], i["code"], i["detail"]))
        return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Assemble a bid submission folder.")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any ERROR-severity issue was raised")
    args = ap.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        root = os.path.dirname(os.path.abspath(args.manifest))
        result = BidPack(manifest, root).assemble(args.out)
    except (ManifestError, PaginationError) as exc:
        sys.stderr.write("REFUSED: %s\n" % exc)
        return 2
    r = result["readiness"]
    print("assembled -> %s" % args.out)
    print("  proposal.pdf: %d pages (%d bytes), pagination settled in %d pass(es)"
          % (result["render"]["pdf_pages"], result["render"]["pdf_bytes"],
             result["render"]["pagination_passes"]))
    print("  sections: %d   attachments: %d" % (len(result["sections"]), len(result["attachments"])))
    print("  required attachments declared %d / present %d / NOT SUPPLIED %d %s"
          % (r["required_declared"], r["required_present"],
             len(r["required_not_supplied"]),
             ("(%s)" % ", ".join(r["required_not_supplied"])) if r["required_not_supplied"] else ""))
    print("  status: %s" % r["status"])
    for i in result["issues"]:
        print("  [%-5s] %-42s %s" % (i["severity"], i["code"], i["detail"]))
    if args.strict and any(i["severity"] == ERROR for i in result["issues"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
