"""UIOWA-136B -- structural validator for the rendered submission documents.

WHY THIS EXISTS, STATED PLAINLY
-------------------------------
`pdfwrite.py` writes a PDF and also reads it back, and the UIOWA-136 tests
assert against that readback. That is better than trusting the builder's own
report -- and it is still circular in one specific way: the writer and the
reader are the same author making the same assumptions. If both misunderstand
the format in the same place they agree perfectly, every test is green, and the
file still does not open in Acrobat or Preview.

So this module does NOT use pdfwrite's reader. It parses the bytes from scratch
and checks them against the format's own internal rules: does the xref offset
actually land on the object it claims, does /Length equal the real stream
length, does every indirect reference resolve, does the page tree's /Count match
reality, does every link destination exist in this document.

WHAT A PASS MEANS, AND WHAT IT DOES NOT
---------------------------------------
A pass means "no structural defect found by these checks". It does NOT mean
"valid PDF", it does NOT mean the page looks right, and it is NOT a PDF/UA,
WCAG or any other conformance statement. This module makes no compliance claim
and issues no certificate. Checks that were not run are reported as NOT RUN --
never as a pass.

Run:
    python3 packcheck.py sample_output/proposal.pdf sample_output/proposal.docx
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

OK, DEFECT = "OK", "DEFECT"


class Report(object):
    """A checked/unchecked record. Absence of a check is never a pass.

    Four outcomes, and the distinction between the last three is the whole
    point of this class:
      ok       -- the check ran and the file satisfied it
      defect   -- the check ran and the file failed it
      note     -- an advisory observation; NOT a defect, does not fail the file
      not_run  -- the check did not run, either because it does not apply or
                  because this validator CANNOT ASSESS this input. Never a pass.

    `note` exists because of a real false positive: this module used to demand
    `word/styles.xml` in every .docx -- not because OOXML requires it, but
    because its sibling writer happens to emit it. It reported another seat's
    perfectly valid fixture as broken. A false positive against a correct file
    is worse than a missed defect: it burns the other author's time arguing
    with the tool. Conventions are notes. Only requirements are defects.
    """

    def __init__(self, target):
        self.target = target
        self.checks = []      # (name, OK|DEFECT, detail)
        self.notes = []       # (name, detail)
        self.not_run = []     # (name, why)

    def ok(self, name, detail=""):
        self.checks.append((name, OK, detail))

    def defect(self, name, detail):
        self.checks.append((name, DEFECT, detail))

    def note(self, name, detail):
        self.notes.append((name, detail))

    def skip(self, name, why):
        self.not_run.append((name, why))

    def unassessed(self, name, why):
        """This validator cannot evaluate the check on this input."""
        self.not_run.append((name, "CANNOT ASSESS: " + why))

    @property
    def defects(self):
        return [(n, d) for n, s, d in self.checks if s == DEFECT]

    @property
    def defect_names(self):
        return [n for n, _ in self.defects]

    @property
    def note_names(self):
        return [n for n, _ in self.notes]

    @property
    def unassessed_names(self):
        return [n for n, w in self.not_run if w.startswith("CANNOT ASSESS")]

    @property
    def clean(self):
        return not self.defects

    @property
    def verdict(self):
        if self.defects:
            return "DEFECTS(%d)" % len(self.defects)
        if not self.checks:
            return "NOT ASSESSED"
        if self.unassessed_names:
            return "CLEAN/PARTIAL"
        return "CLEAN"

    def summary(self):
        return ("%s: %d check(s) run, %d defect(s), %d note(s), %d not run"
                % (self.target, len(self.checks), len(self.defects),
                   len(self.notes), len(self.not_run)))

    def lines(self):
        out = [self.summary()]
        for n, s, d in self.checks:
            out.append("  [%s] %-30s %s" % ("ok " if s == OK else "DEF", n, d))
        for n, d in self.notes:
            out.append("  [note] %-28s %s" % (n, d))
        for n, why in self.not_run:
            out.append("  [---] %-30s NOT RUN: %s" % (n, why))
        return out


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

_OBJ_HEAD = re.compile(rb"(?m)^(\d+)\s+(\d+)\s+obj\b")


def _pdf_bodies(data, real):
    """object number -> raw bytes between 'obj' and 'endobj', scanned from the file."""
    out = {}
    for num, start in real.items():
        m = _OBJ_HEAD.match(data, start)
        end = data.find(b"endobj", m.end())
        out[num] = data[m.end():end if end > 0 else len(data)]
    return out


def check_pdf(data, target="pdf"):
    r = Report(target)

    if not data.startswith(b"%PDF-"):
        r.defect("header", "file does not begin with %PDF-")
        return r
    r.ok("header", data[:8].decode("latin-1"))

    if not data.rstrip().endswith(b"%%EOF"):
        r.defect("eof_marker", "file does not end with %%EOF (truncated?)")
    else:
        r.ok("eof_marker")

    # Where the objects REALLY are, found by scanning the bytes -- not by
    # trusting the xref table we are about to check.
    real = {}
    for m in _OBJ_HEAD.finditer(data):
        real[int(m.group(1))] = m.start()
    if not real:
        r.defect("objects_present", "no 'N G obj' headers found")
        return r
    r.ok("objects_present", "%d object(s)" % len(real))

    # PDF 1.5+ may store the cross-reference table as a compressed stream object
    # and pack objects into object streams. This validator parses neither. That
    # is a COVERAGE LIMIT, not a defect in the file, and it has to be reported
    # as CANNOT ASSESS -- reporting it as broken would be a false positive
    # against every seat using a real PDF library.
    xref_stream = b"/Type /XRef" in data or b"/Type/XRef" in data
    obj_stream = b"/Type /ObjStm" in data or b"/Type/ObjStm" in data

    sx = re.search(rb"startxref\s+(\d+)\s*%%EOF\s*$", data)
    xref_at = None
    if not sx:
        r.defect("startxref", "no trailing startxref/%%EOF pair")
    else:
        xref_at = int(sx.group(1))
        if xref_at >= len(data) or data[xref_at:xref_at + 4] != b"xref":
            if xref_stream and _OBJ_HEAD.match(data, xref_at):
                r.unassessed("startxref", "points at a cross-reference stream "
                             "(PDF 1.5+); this validator reads classic xref tables only")
            else:
                r.defect("startxref",
                         "startxref %d does not point at an 'xref' keyword" % xref_at)
            xref_at = None
        else:
            r.ok("startxref", "offset %d" % xref_at)
    if obj_stream:
        r.unassessed("objects_in_object_streams",
                     "file uses object streams (/ObjStm); objects packed inside "
                     "them are not visible to this validator")

    offsets = {}
    if xref_at is not None:
        head = re.match(rb"xref\s+(\d+)\s+(\d+)\s+", data[xref_at:])
        if not head:
            r.defect("xref_subsection", "xref table has no 'first count' header")
        else:
            first, count = int(head.group(1)), int(head.group(2))
            body_at = xref_at + head.end()
            entries = re.findall(rb"(\d{10}) (\d{5}) ([nf])",
                                 data[body_at:body_at + count * 20 + 40])
            if len(entries) < count:
                r.defect("xref_entry_count",
                         "header says %d entries, found %d" % (count, len(entries)))
            else:
                r.ok("xref_entry_count", "%d entries" % count)
            for i, (off, _gen, kind) in enumerate(entries[:count]):
                if kind == b"n":
                    offsets[first + i] = int(off)

    # THE check this module exists for. An off-by-one here produces a file that
    # opens in one viewer and fails in another, and a same-author reader would
    # never notice because it never uses the xref table at all.
    bad = []
    for num, off in sorted(offsets.items()):
        if off <= 0 or off >= len(data):
            bad.append("obj %d -> offset %d out of range" % (num, off))
            continue
        m = _OBJ_HEAD.match(data, off)
        if not m:
            bad.append("obj %d -> offset %d is not an object header" % (num, off))
        elif int(m.group(1)) != num:
            bad.append("obj %d -> offset %d holds object %s"
                       % (num, off, m.group(1).decode()))
    if bad:
        r.defect("xref_offsets_resolve", "; ".join(bad[:4]))
    elif offsets:
        r.ok("xref_offsets_resolve", "%d offset(s) land on their object" % len(offsets))
    elif xref_stream:
        r.unassessed("xref_offsets_resolve", "cross-reference stream (PDF 1.5+)")
    else:
        r.skip("xref_offsets_resolve", "no in-use xref entries were parsed")

    trailer = re.search(rb"trailer\s*<<(.*?)>>\s*startxref", data, re.S)
    tdict = b""
    if not trailer and xref_stream:
        # In a 1.5+ file the trailer fields live in the XRef stream's own dict.
        xr = re.search(rb"<<([^<>]*?/Type\s*/XRef.*?)>>", data, re.S)
        tdict = xr.group(1) if xr else b""
        r.unassessed("trailer", "trailer fields are carried in a cross-reference "
                     "stream dictionary; read for /Root only, not validated")
    elif not trailer:
        r.defect("trailer", "no trailer dictionary")
    else:
        tdict = trailer.group(1)
        size = re.search(rb"/Size\s+(\d+)", tdict)
        if size is None and xref_stream:
            r.unassessed("trailer_size", "cross-reference stream (PDF 1.5+)")
        elif not size:
            r.defect("trailer_size", "trailer has no /Size")
        elif int(size.group(1)) <= max(real):
            r.defect("trailer_size", "/Size %s but highest object number is %d"
                     % (size.group(1).decode(), max(real)))
        else:
            r.ok("trailer_size", "/Size %s" % size.group(1).decode())

    bodies = _pdf_bodies(data, real)

    # /Length must equal the real stream length.
    #
    # The EOL before `endstream` is optional and is NOT part of the data: some
    # producers write `<data>\nendstream`, some write `<data>endstream`, some
    # write CRLF. An earlier version of this check searched for b"\nendstream"
    # and so reported every Flate-compressed PDF whose binary data runs straight
    # into the keyword as broken -- a false positive found by pointing this tool
    # at another lane's file. The tolerance below is exactly the spec-permitted
    # 0, 1 or 2 bytes of end-of-line, and nothing wider.
    wrong, streams = [], 0
    for num, body in bodies.items():
        m = re.search(rb"/Length\s+(\d+)", body)
        if not m:
            continue
        sm = re.search(rb"stream(?:\r\n|\n|\r)", body)
        if not sm:
            wrong.append("obj %d declares /Length but has no stream" % num)
            continue
        streams += 1
        at = body.rfind(b"endstream")
        if at < sm.end():
            wrong.append("obj %d stream has no endstream keyword" % num)
            continue
        measured, declared = at - sm.end(), int(m.group(1))
        slack = measured - declared
        if slack not in (0, 1, 2):
            wrong.append("obj %d /Length %d but %d byte(s) sit between stream and "
                         "endstream" % (num, declared, measured))
    if wrong:
        r.defect("stream_lengths", "; ".join(wrong[:4]))
    else:
        r.ok("stream_lengths", "%d stream(s) measured (+/-2 bytes of "
             "permitted end-of-line)" % streams)

    dangling = set()
    for num, body in bodies.items():
        for ref in re.findall(rb"(\d+)\s+0\s+R\b", body):
            if int(ref) not in real:
                dangling.add("obj %d -> %s 0 R (no such object)" % (num, ref.decode()))
    if obj_stream:
        r.unassessed("references_resolve", "objects may be packed in object "
                     "streams, so an unresolved reference cannot be distinguished "
                     "from one this validator simply cannot see")
    elif dangling:
        r.defect("references_resolve", "; ".join(sorted(dangling)[:4]))
    else:
        r.ok("references_resolve", "all indirect references resolve")

    root = re.search(rb"/Root\s+(\d+)\s+0\s+R", tdict)
    if not root:
        if xref_stream or obj_stream:
            r.unassessed("catalog", "no readable /Root outside the compressed "
                         "cross-reference/object streams")
        else:
            r.defect("catalog", "trailer has no /Root")
        return r
    cat = bodies.get(int(root.group(1)), b"")
    if b"/Type /Catalog" not in cat:
        if obj_stream:
            r.unassessed("catalog", "/Root object is not visible outside an object stream")
        else:
            r.defect("catalog", "/Root %s is not a /Catalog" % root.group(1).decode())
        return r
    r.ok("catalog", "object %s" % root.group(1).decode())

    pm = re.search(rb"/Pages\s+(\d+)\s+0\s+R", cat)
    if not pm:
        r.defect("page_tree", "catalog has no /Pages")
        return r
    ptree = bodies.get(int(pm.group(1)), b"")
    kids_m = re.search(rb"/Kids\s*\[(.*?)\]", ptree, re.S)
    count_m = re.search(rb"/Count\s+(\d+)", ptree)
    kids = [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", kids_m.group(1))] if kids_m else []
    if not kids:
        r.defect("page_tree", "/Pages has no /Kids")
        return r
    r.ok("page_tree", "object %s" % pm.group(1).decode())
    if not count_m or int(count_m.group(1)) != len(kids):
        r.defect("page_count", "/Count %s but %d kid(s)"
                 % (count_m.group(1).decode() if count_m else "absent", len(kids)))
    else:
        r.ok("page_count", "%d page(s)" % len(kids))

    notpages = [k for k in kids if b"/Type /Page" not in bodies.get(k, b"")]
    if notpages:
        r.defect("kids_are_pages", "kid object(s) %s are not /Type /Page"
                 % ", ".join(str(k) for k in notpages[:4]))
    else:
        r.ok("kids_are_pages")

    kidset = set(kids)
    baddest, ndest = [], 0
    for num, body in bodies.items():
        for d in re.findall(rb"/Dest\s*\[\s*(\d+)\s+0\s+R", body):
            ndest += 1
            if int(d) not in kidset:
                baddest.append("obj %d -> /Dest page %s not in the page tree"
                               % (num, d.decode()))
    if baddest:
        r.defect("destinations_in_document", "; ".join(baddest[:4]))
    else:
        r.ok("destinations_in_document", "%d destination(s) checked" % ndest)

    annots = []
    for k in kids:
        am = re.search(rb"/Annots\s*\[(.*?)\]", bodies.get(k, b""), re.S)
        if am:
            annots += [int(x) for x in re.findall(rb"(\d+)\s+0\s+R", am.group(1))]
    missing = [a for a in annots if b"/Subtype /Link" not in bodies.get(a, b"")]
    if missing:
        r.defect("annots_are_links", "annot object(s) %s are not /Link"
                 % ", ".join(str(a) for a in missing[:4]))
    elif annots:
        r.ok("annots_are_links", "%d link annotation(s)" % len(annots))
    else:
        r.skip("annots_are_links", "this document has no annotations")

    unresolved = []
    for k in kids:
        pbody = bodies.get(k, b"")
        fm = re.search(rb"/Font\s*<<(.*?)>>", pbody, re.S)
        declared = set(re.findall(rb"/([A-Za-z0-9]+)\s+\d+\s+0\s+R", fm.group(1))) if fm else set()
        cm = re.search(rb"/Contents\s+(\d+)\s+0\s+R", pbody)
        if not cm:
            continue
        used = set(re.findall(rb"/([A-Za-z0-9]+)\s+[\d.]+\s+Tf",
                              bodies.get(int(cm.group(1)), b"")))
        for f in sorted(used - declared):
            unresolved.append("page obj %d uses /%s which is not in its /Resources"
                              % (k, f.decode()))
    if unresolved:
        r.defect("fonts_declared", "; ".join(unresolved[:4]))
    else:
        r.ok("fonts_declared")

    om = re.search(rb"/Outlines\s+(\d+)\s+0\s+R", cat)
    if not om:
        r.skip("outline_chain", "catalog declares no /Outlines")
    else:
        node = bodies.get(int(om.group(1)), b"")
        first = re.search(rb"/First\s+(\d+)\s+0\s+R", node)
        if not first:
            r.skip("outline_chain", "outline root has no /First (empty outline)")
        else:
            cur, seen, n, broke = int(first.group(1)), set(), 0, None
            while cur is not None:
                if cur in seen:
                    broke = "outline chain loops at object %d" % cur
                    break
                if cur not in real:
                    broke = "outline chain reaches missing object %d" % cur
                    break
                seen.add(cur)
                n += 1
                nx = re.search(rb"/Next\s+(\d+)\s+0\s+R", bodies[cur])
                cur = int(nx.group(1)) if nx else None
            if broke:
                r.defect("outline_chain", broke)
            else:
                r.ok("outline_chain", "%d item(s), terminates" % n)
    return r


# --------------------------------------------------------------------------
# DOCX (OOXML package)
# --------------------------------------------------------------------------

# Genuinely mandatory for an OOXML package to be openable: the content-type
# map, the package relationships, and whatever main document part those
# relationships point at (discovered, NOT hardcoded).
MANDATORY_PARTS = ("[Content_Types].xml", "_rels/.rels")

# Conventional, and emitted by this lane's own writer -- but NOT required by
# OOXML. Absence is a NOTE. Demanding these was a real false positive against
# another seat's valid fixture; see the Report docstring.
CONVENTIONAL_PARTS = ("word/styles.xml", "docProps/core.xml")

OFFICE_DOC_REL = "/officeDocument"


def _main_document_part(z, names):
    """Find the main document part through the package relationships.

    Hardcoding 'word/document.xml' is the same author's-assumption mistake that
    produced the styles.xml false positive: the path is whatever _rels/.rels
    says it is.
    """
    if "_rels/.rels" not in names:
        return None, "no _rels/.rels"
    try:
        root = ET.fromstring(z.read("_rels/.rels"))
    except ET.ParseError as exc:
        return None, "_rels/.rels is not well-formed XML (%s)" % exc
    for rel in root:
        if rel.get("Type", "").endswith(OFFICE_DOC_REL):
            return rel.get("Target", "").lstrip("/"), None
    return None, "package declares no officeDocument relationship"


def check_docx(path, target=None):
    r = Report(target or path)
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        r.defect("zip_container", "not a readable zip: %s" % exc)
        return r
    with z:
        try:
            bad = z.testzip()
        except Exception as exc:                       # noqa: BLE001 - report, don't crash
            r.defect("zip_container", "unreadable member: %s" % exc)
            return r
        if bad:
            r.defect("zip_container", "corrupt member: %s" % bad)
            return r
        names = set(z.namelist())
        r.ok("zip_container", "%d part(s)" % len(names))

        gone = [p for p in MANDATORY_PARTS if p not in names]
        if gone:
            r.defect("mandatory_parts", "missing: %s" % ", ".join(gone))
        else:
            r.ok("mandatory_parts", ", ".join(MANDATORY_PARTS))

        main_part, why = _main_document_part(z, names)
        if main_part is None:
            r.defect("main_document_part", why)
        elif main_part not in names:
            r.defect("main_document_part",
                     "relationships point at %r, which is not in the package" % main_part)
        else:
            r.ok("main_document_part", main_part)

        absent = [p for p in CONVENTIONAL_PARTS if p not in names]
        if absent:
            # NOT a defect. OOXML does not require these; this lane's writer
            # simply emits them.
            r.note("conventional_parts",
                   "absent (not required by OOXML): %s" % ", ".join(absent))

        xml_parts = [n for n in names if n.endswith((".xml", ".rels"))]
        malformed = []
        for n in xml_parts:
            try:
                ET.fromstring(z.read(n))
            except ET.ParseError as exc:
                malformed.append("%s (%s)" % (n, exc))
        if malformed:
            r.defect("xml_well_formed", "; ".join(malformed[:3]))
        else:
            r.ok("xml_well_formed", "%d XML part(s) parsed" % len(xml_parts))

        broken = []
        for rels in [n for n in names if n.endswith(".rels")]:
            base = rels.rsplit("_rels/", 1)[0]
            try:
                root = ET.fromstring(z.read(rels))
            except ET.ParseError:
                continue
            for rel in root:
                tgt = rel.get("Target", "")
                if rel.get("TargetMode") == "External" or tgt.startswith(("http:", "https:")):
                    continue
                cand = (base + tgt).lstrip("/")
                if cand not in names:
                    broken.append("%s -> %s" % (rels, tgt))
        if broken:
            r.defect("relationships_resolve", "; ".join(broken[:4]))
        else:
            r.ok("relationships_resolve")

        if not main_part or main_part not in names:
            r.skip("internal_anchors_resolve", "no readable main document part")
            r.skip("bookmarks_balanced", "no readable main document part")
            return r

        doc = z.read(main_part).decode("utf-8", "replace")
        marks = set(re.findall(r'<w:bookmarkStart [^>]*w:name="([^"]+)"', doc))
        links = re.findall(r'<w:hyperlink w:anchor="([^"]+)"', doc)
        dead = sorted({l for l in links if l not in marks})
        if dead:
            r.defect("internal_anchors_resolve",
                     "hyperlink(s) with no bookmark: %s" % ", ".join(dead[:4]))
        elif links:
            r.ok("internal_anchors_resolve",
                 "%d link(s) -> %d bookmark(s)" % (len(links), len(marks)))
        else:
            r.skip("internal_anchors_resolve", "document has no internal hyperlinks")

        starts = re.findall(r'<w:bookmarkStart [^>]*w:id="(\d+)"', doc)
        ends = re.findall(r'<w:bookmarkEnd w:id="(\d+)"', doc)
        if sorted(starts) != sorted(ends):
            r.defect("bookmarks_balanced",
                     "%d bookmarkStart vs %d bookmarkEnd" % (len(starts), len(ends)))
        else:
            r.ok("bookmarks_balanced", "%d pair(s)" % len(starts))
    return r


# --------------------------------------------------------------------------

def check_path(path):
    """Route one path to the right checker, or record that nothing was checked."""
    if path.lower().endswith(".pdf"):
        try:
            with open(path, "rb") as fh:
                return check_pdf(fh.read(), path)
        except OSError as exc:
            rep = Report(path)
            rep.defect("readable", str(exc))
            return rep
    if path.lower().endswith(".docx"):
        return check_docx(path)
    rep = Report(path)
    rep.skip("format", "not a .pdf or .docx; nothing was checked")
    return rep


def sweep(root):
    """Audit every .pdf/.docx under `root`, in sorted order for reproducibility."""
    found = []
    for base, _dirs, files in os.walk(root):
        for name in sorted(files):
            if name.lower().endswith((".pdf", ".docx")):
                found.append(os.path.join(base, name))
    return [check_path(p) for p in sorted(found)]


def sweep_table(reports, root=""):
    w = max([len(_rel(r.target, root)) for r in reports] + [8])
    out = ["%-*s  %6s %7s %5s %10s  %s"
           % (w, "document", "checks", "defects", "notes", "unassessed", "verdict"),
           "-" * (w + 45)]
    for r in reports:
        out.append("%-*s  %6d %7d %5d %10d  %s"
                   % (w, _rel(r.target, root), len(r.checks), len(r.defects),
                      len(r.notes), len(r.unassessed_names), r.verdict))
    return out


def _rel(path, root):
    return os.path.relpath(path, root) if root else path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--sweep":
        if len(argv) != 2:
            sys.stderr.write("usage: packcheck.py --sweep <directory>\n")
            return 2
        root = argv[1]
        reports = sweep(root)
        if not reports:
            print("no .pdf or .docx files found under %s" % root)
            print("Nothing was checked. That is NOT a pass.")
            return 0
        for line in sweep_table(reports, root):
            print(line)
        defects = [r for r in reports if r.defects]
        print("")
        for r in defects:
            for n, d in r.defects:
                print("DEFECT  %s  %s: %s" % (_rel(r.target, root), n, d))
        for r in reports:
            for n, d in r.notes:
                print("note    %s  %s: %s" % (_rel(r.target, root), n, d))
            for n in r.unassessed_names:
                why = dict(r.not_run)[n]
                print("unasses %s  %s: %s" % (_rel(r.target, root), n, why))
        print("\n%d file(s) swept, %d with defect(s)." % (len(reports), len(defects)))
        print("A clean result means: no structural defect found by these checks. It is "
              "not a validity, PDF/UA, WCAG or any other conformance claim. Anything "
              "marked CANNOT ASSESS was not checked and is not a pass.")
        return 1 if defects else 0

    if not argv:
        sys.stderr.write("usage: packcheck.py <file.pdf|file.docx> [...]\n"
                         "       packcheck.py --sweep <directory>\n")
        return 2
    reports = []
    for path in argv:
        if path.lower().endswith(".pdf"):
            try:
                with open(path, "rb") as fh:
                    reports.append(check_pdf(fh.read(), path))
            except OSError as exc:
                rep = Report(path)
                rep.defect("readable", str(exc))
                reports.append(rep)
        elif path.lower().endswith(".docx"):
            reports.append(check_docx(path))
        else:
            rep = Report(path)
            rep.skip("format", "not a .pdf or .docx; nothing was checked")
            reports.append(rep)
    for rep in reports:
        for line in rep.lines():
            print(line)
    total = sum(len(r.defects) for r in reports)
    print("\n%d defect(s) across %d file(s)." % (total, len(reports)))
    print("A clean result means: no structural defect found by these checks. It is "
          "not a validity, PDF/UA, WCAG or any other conformance claim.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
