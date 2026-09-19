"""Offline, review-only bid assembler. It never represents a complete bid.

Build: python assembler.py build inputs/packet.json /new/review-folder
Verify: python assembler.py verify /new/review-folder
Dependencies: python-docx, reportlab, PyMuPDF. No network or provider writes.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any

STATUS = 'PARTIAL REVIEW DRAFT - NOT FOR SUBMISSION'
NOTICE = ('Assembly integrity is not bid completeness, approval, qualification, '
          'acceptance of terms, a contract, payment or authority to submit.')
FILES = ('00_START_HERE.html', '01_REVIEW_DRAFT.docx', '01_REVIEW_DRAFT.pdf',
         '02_ATTACHMENT_INDEX.json', '03_FINANCIALS_MISSING.txt',
         '04_QUALIFICATIONS_MISSING.txt', '05_COMMERCIAL_SOURCE.md',
         '06_REQUIREMENTS.json', '07_MANIFEST.json', '08_SOURCE_REGISTER.md')


class AssemblyError(ValueError):
    """Invalid inputs, incomplete custody or malformed output."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_digest(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def strict_json(data: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise AssemblyError(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def bad_constant(value):
        raise AssemblyError(f'non-finite JSON number: {value}')
    return json.loads(data, object_pairs_hook=pairs, parse_constant=bad_constant)


def text(value: Any, name: str, maximum: int = 20000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise AssemblyError(f'{name}: expected nonempty bounded text')
    if any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise AssemblyError(f'{name}: control character')
    return value


def local_name(value: Any) -> str:
    value = text(value, 'filename', 120)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value) or '..' in value:
        raise AssemblyError('filename must be a single portable relative component')
    return value


def read_regular(path: Path, maximum: int = 2000000) -> bytes:
    """Bounded no-follow read. Trusted parent dirs; not an adversarial sandbox."""
    path = Path(path)
    for component in (path, *path.parents):
        if component.is_symlink():
            raise AssemblyError(f'symlink refused: {component}')
    try:
        with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)), 'rb') as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
                raise AssemblyError('not a bounded regular file')
            data = handle.read(maximum + 1)
            after = os.fstat(handle.fileno())
        visible = path.stat()
    except OSError as exc:
        raise AssemblyError(f'cannot read {path.name}: {exc}') from exc
    fingerprint = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if len(data) > maximum or fingerprint(before) != fingerprint(after) or fingerprint(after) != fingerprint(visible):
        raise AssemblyError('input changed while reading')
    return data


def load_packet(path: Path) -> tuple[dict, bytes]:
    packet = strict_json(read_regular(path).decode('utf-8'))
    if not isinstance(packet, dict) or set(packet) != {'schema', 'title', 'source', 'requirements'}:
        raise AssemblyError('packet keys do not match schema')
    if type(packet['schema']) is not int or packet['schema'] != 1:
        raise AssemblyError('unsupported schema')
    text(packet['title'], 'title', 100)
    source = packet['source']
    if not isinstance(source, dict) or set(source) != {'filename', 'sha256', 'git_blob_sha', 'repository_path', 'retrieved_on'}:
        raise AssemblyError('source keys do not match schema')
    name = local_name(source['filename'])
    for key, length in (('sha256', 64), ('git_blob_sha', 40)):
        if not isinstance(source[key], str) or not re.fullmatch('[0-9a-f]{' + str(length) + '}', source[key]):
            raise AssemblyError(f'invalid {key}')
    for key in ('repository_path', 'retrieved_on'):
        text(source[key], key, 300)
    data = read_regular(path.parent / name)
    if digest(data) != source['sha256'] or git_digest(data) != source['git_blob_sha']:
        raise AssemblyError('SOURCE_HASH_MISMATCH: rebuild input binding after reviewing the new source')
    data.decode('utf-8')
    requirements = packet['requirements']
    if not isinstance(requirements, list) or not requirements or len(requirements) > 20:
        raise AssemblyError('requirements must be a nonempty bounded list')
    seen = set()
    for item in requirements:
        if not isinstance(item, dict) or set(item) != {'id', 'locator', 'requirement', 'status'}:
            raise AssemblyError('requirement keys do not match schema')
        key = local_name(item['id'])
        if key.casefold() in seen:
            raise AssemblyError('duplicate requirement ID')
        seen.add(key.casefold())
        text(item['locator'], 'locator', 200)
        text(item['requirement'], 'requirement', 1000)
        if item['status'] not in {'MISSING', 'PARTIAL', 'REVIEW_REQUIRED', 'REFERENCE_ONLY'}:
            raise AssemblyError('unknown or authorizing requirement status')
    # This reviewed sample covers all seven declared RFQ obligations; additions require review.
    if seen != {'proposal', 'financials', 'references', 'team', 'fee', 'exceptions', 'agency-docs'}:
        raise AssemblyError('requirement universe drift; seven reviewed obligations are required')
    return packet, data


def sections(packet: dict, source: bytes) -> list[dict]:
    """One content model drives DOCX, PDF and the complete offline HTML view."""
    req = packet['requirements']
    return [
        {'id': 'index', 'title': 'Attachment index', 'body': [
            'This is a review folder, not an upload folder. Files marked MISSING are explanatory placeholders, not substitutes for bidder evidence.',
            '01_REVIEW_DRAFT.pdf / .docx - assembled technical workshare and review notes. PARTIAL: complete prime proposal and eBid responses are not supplied.',
            '03_FINANCIALS_MISSING.txt - MISSING financial evidence; see Financial attachment gap.',
            '04_QUALIFICATIONS_MISSING.txt - MISSING prime qualifications; see Qualification inputs.',
            '05_COMMERCIAL_SOURCE.md - supplied commercial source, unchanged. Proposed subcontract terms, not the University bid fee.',
            '06_REQUIREMENTS.json - original-edition reconciliation, not a current compliance certification.',
            '07_MANIFEST.json - exact output-file hashes and source identity. Integrity only.'], 'refs': ['financials', 'qualifications', 'reconciliation']},
        {'id': 'workshare', 'title': 'Assembled technical workshare', 'body': [
            'The following is the supplied COMMERCIAL.md, rendered without rewriting its terms. Markdown styling is presentation only. Source identity is in the version register.',
            *source.decode('utf-8').strip().split('\n\n')], 'refs': ['versions']},
        {'id': 'financials', 'title': 'Financial attachment gap', 'body': [
            'MISSING - DO NOT UPLOAD THIS PLACEHOLDER AS FINANCIAL EVIDENCE.',
            'No financial statements, annual reports, auditor opinion, fiscal-year periods or disclosure approval were supplied to this assembler.',
            'The original RFQ identifies a required financial attachment covering audited statements and annual reports for the preceding two years (printed p.2; attribute 19 on p.11). The prime must determine the applicable reporting periods and provide genuine documents through an authorized private channel.',
            'This folder does not contain synthetic financial statements. Nothing here establishes financial capacity or eligibility. Restricted financial evidence must not be committed to the public Commons repository.',
            'Before any authorized submission: verify current instructions; obtain the required documents from the prime; reconcile file versions and reporting periods; replace this gap in a private bid assembly. This tool does not make those decisions.'], 'refs': ['index', 'reconciliation']},
        {'id': 'qualifications', 'title': 'Qualification inputs', 'body': [
            'MISSING - THESE ARE INPUT QUESTIONS, NOT QUALIFICATIONS.',
            'The complete prime methodology, schedule, named team and qualifications, reference details, all-inclusive bid fee and assumptions have not been supplied. The technical workshare cannot stand in for those bidder representations.',
            'Reference inputs: identify three genuine comparable engagements and authorized reference contacts. Do not invent institutions, people, experience or contact details (original RFQ attribute 10).',
            'Team inputs: obtain named personnel, accountable manager, roles and supported qualifications from the prime (attributes 9 and 11). No person is scheduled or committed by this folder.',
            'The figures in the assembled workshare are proposed TJLabs subcontract economics only. Travel is excluded from that workshare. The prime must independently determine its all-inclusive response price; this package supplies no prime bid price.',
            'The no-exceptions/terms response remains REVIEW REQUIRED, not automatically answered. An empty-looking field must not be treated as a safe default certification.'], 'refs': ['workshare', 'reconciliation']},
        {'id': 'reconciliation', 'title': 'RFQ reconciliation and currentness', 'body': [
            'CURRENT AMENDMENT NOT VERIFIED. The inspected original invitation was issued August 31, 2026 and shows September 22, 2026, 3 PM Central. The prepared workshare reports September 29, 2026, 3 PM Central. No current amendment was supplied to this assembler. Neither date is promoted here to a verified submission deadline.',
            *[f"{r['id'].upper()} | {r['status']} | {r['locator']}\n{r['requirement']}" for r in req],
            'This review covers the declared attachment obligations only. It does not claim that all 36 eBid attributes have been rendered or satisfied. A verified current solicitation, addenda, complete field responses and prime approval remain outside this partial draft.'], 'refs': ['financials', 'qualifications', 'versions']},
        {'id': 'versions', 'title': 'Source and version register', 'body': [
            'Supplied source: ' + packet['source']['repository_path'],
            'Git blob: ' + packet['source']['git_blob_sha'],
            'SHA-256: ' + packet['source']['sha256'],
            'Source retrieval date: ' + packet['source']['retrieved_on'] + '. Original author attribution is retained in the parent workshare; assembly by ZZ-IRIDIUM-Q2B9.',
            'RFQ source: original invitation, printed pp.2, 9-11, read on September 19, 2026. Retrieved through a public document mirror; current official amendment not independently verified. Exact source locations and retrieval route are supplied in 08_SOURCE_REGISTER.md.',
            'Navigation: use this document\'s Contents links or the Word Navigation pane. All section references target bookmarks; page numbers are field-backed in DOCX and fixed to this PDF. Regenerate after edits; do not rely on cached page references in a manually changed document.',
            'Repeatability: unchanged inputs produce byte-identical generated outputs in the pinned dependency environment. Hashes bind the supplied bytes, not truth, rights to disclose, current solicitation status or external approval.',
            NOTICE], 'refs': ['index', 'workshare']},
    ]


def plain(value: str) -> str:
    """Remove Markdown styling, retaining the words and list boundaries."""
    value = re.sub(r'^#{1,6}\s+', '', value, flags=re.M)
    return value.replace('**', '').replace('`', '')


def make_docx(path: Path, packet: dict, content: list[dict]) -> None:
    from datetime import datetime, timezone
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor
    document = Document()
    props = document.core_properties
    props.title = packet['title']; props.author = 'TJLabs | ZZ-IRIDIUM-Q2B9'
    props.subject = STATUS; props.created = props.modified = datetime(2026, 9, 19, tzinfo=timezone.utc)
    props.revision = 1
    sec = document.sections[0]
    sec.page_width = Inches(8.5); sec.page_height = Inches(11)
    sec.top_margin = sec.bottom_margin = Inches(.7)
    sec.left_margin = sec.right_margin = Inches(.75)
    for name in ('Normal', 'Title', 'Heading 1', 'Heading 2'):
        document.styles[name].font.name = 'Calibri'
    normal = document.styles['Normal']
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.08
    for name, size in [('Heading 1', 19), ('Heading 2', 12)]:
        document.styles[name].font.size = Pt(size)
        document.styles[name].font.color.rgb = RGBColor.from_string('183749')
    sec.header.paragraphs[0].text = 'TJLabs  /  RFQ 18649  /  REVIEW COPY'
    sec.header.paragraphs[0].style = 'Caption'
    footer = sec.footer.paragraphs[0]
    footer.text = 'NOT FOR SUBMISSION  |  '
    field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    def bookmark(paragraph, name, number):
        start = OxmlElement('w:bookmarkStart'); start.set(qn('w:id'), str(number)); start.set(qn('w:name'), name)
        end = OxmlElement('w:bookmarkEnd'); end.set(qn('w:id'), str(number))
        paragraph._p.insert(0, start); paragraph._p.append(end)
    def link(paragraph, target, label, page):
        anchor = OxmlElement('w:hyperlink'); anchor.set(qn('w:anchor'), target)
        run = OxmlElement('w:r'); rp = OxmlElement('w:rPr')
        color = OxmlElement('w:color'); color.set(qn('w:val'), '165A77'); rp.append(color); run.append(rp)
        t = OxmlElement('w:t'); t.text = label; run.append(t); anchor.append(run); paragraph._p.append(anchor)
        paragraph.add_run(' — page ')
        field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGEREF ' + target + ' \\h')
        run = OxmlElement('w:r'); t = OxmlElement('w:t'); t.text = str(page); run.append(t); field.append(run); paragraph._p.append(field)
    document.add_paragraph('RFQ 18649', 'Subtitle')
    document.add_heading(packet['title'], 0)
    document.add_paragraph(STATUS, 'Heading 2')
    document.add_paragraph('Prepared components for prospective prime review. This is not a complete prime proposal, an eBid response or a representation of Clark\'s acceptance.')
    document.add_paragraph('Missing: current amendment, complete prime response, financial evidence, named qualifications and prime bid fee. No financial or qualification documents have been invented.')
    document.add_heading('Contents', 1)
    for i, item in enumerate(content, 2):
        link(document.add_paragraph(), item['id'], item['title'], i)
    document.add_paragraph(NOTICE)
    pages = {item['id']: i for i, item in enumerate(content, 2)}
    titles = {item['id']: item['title'] for item in content}
    for i, item in enumerate(content, 1):
        document.add_page_break()
        heading = document.add_heading(item['title'], 1); bookmark(heading, item['id'], i)
        for paragraph in item['body']:
            document.add_paragraph(plain(paragraph))
        for ref in item['refs']:
            link(document.add_paragraph(), ref, 'See ' + titles[ref], pages[ref])
    settings = OxmlElement('w:updateFields'); settings.set(qn('w:val'), 'true'); document.settings.element.append(settings)
    document.save(path)
    # Remove template-only thumbnail and unused style definitions, preserve all used styles.
    # Canonical ZIP times/ordering remove archive-clock nondeterminism.
    with zipfile.ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    from lxml import etree
    for filename in ('word/styles.xml', 'word/stylesWithEffects.xml'):
        if filename not in members:
            continue
        root = etree.fromstring(members[filename]); ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        used = {'Normal', 'DefaultParagraphFont', 'TableNormal', 'NoList', 'Title', 'Subtitle', 'Heading1', 'Heading2', 'Caption', 'Header', 'Footer'}
        styles = {s.get(qn('w:styleId')): s for s in root.findall('w:style', ns)}
        pending = list(used)
        while pending:
            node = styles.get(pending.pop())
            if node is None: continue
            for edge in node.findall('w:basedOn', ns) + node.findall('w:link', ns) + node.findall('w:next', ns):
                key = edge.get(qn('w:val'))
                if key not in used: used.add(key); pending.append(key)
        for key, node in styles.items():
            if key not in used: root.remove(node)
        members[filename] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, (2026, 9, 19, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, members[name])


def make_pdf(path: Path, packet: dict, content: list[dict]) -> None:
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
    from reportlab.pdfgen import canvas
    class StableCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            kwargs['invariant'] = 1
            super().__init__(*args, **kwargs)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('Body', fontName='Helvetica', fontSize=10, leading=12.7, spaceAfter=7))
    styles.add(ParagraphStyle('DeckTitle', fontName='Helvetica-Bold', fontSize=26, leading=31, spaceAfter=19))
    styles.add(ParagraphStyle('Section', fontName='Helvetica-Bold', fontSize=19, leading=23, spaceAfter=13, textColor=HexColor('#183749')))
    styles.add(ParagraphStyle('Nav', fontName='Helvetica', fontSize=10, leading=13, spaceAfter=7, textColor=HexColor('#165A77')))
    def p(value, style='Body'):
        try:
            plain(value).encode('cp1252')
        except UnicodeEncodeError as exc:
            raise AssemblyError('UNSUPPORTED_PDF_GLYPH: no silent character substitution') from exc
        escaped = html.escape(plain(value)).replace('\n', '<br/>')
        return Paragraph(escaped, styles[style])
    pages = {item['id']: i for i, item in enumerate(content, 2)}
    titles = {item['id']: item['title'] for item in content}
    def nav(target, prefix=''):
        return Paragraph(f'<link href="#{target}">{html.escape(prefix + titles[target])} — page {pages[target]}</link>', styles['Nav'])
    story = [p('RFQ 18649', 'Section'), p(packet['title'], 'DeckTitle'), p(STATUS),
             p('Prepared components for prospective prime review. This is not a complete prime proposal, an eBid response or a representation of Clark\'s acceptance.'),
             p('Missing: current amendment, complete prime response, financial evidence, named qualifications and prime bid fee. No financial or qualification documents have been invented.'),
             Spacer(1, 12), p('Contents', 'Section')]
    story.extend(nav(item['id']) for item in content)
    story.append(p(NOTICE))
    for item in content:
        story += [PageBreak(), Paragraph(f'<a name="{item["id"]}"/>{html.escape(item["title"])}', styles['Section'])]
        story.extend(p(paragraph) for paragraph in item['body'])
        story.extend(nav(ref, 'See ') for ref in item['refs'])
    def footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(54, 766, 'TJLabs / RFQ 18649 / REVIEW COPY')
        canvas.drawString(54, 32, 'NOT FOR SUBMISSION')
        canvas.drawRightString(558, 32, f'Page {doc.page}')
    class NavigableDocument(SimpleDocTemplate):
        def afterFlowable(self, flowable):
            if hasattr(flowable, 'nav_id'):
                self.canv.bookmarkPage(flowable.nav_id, fit='XYZ', left=0, top=792, zoom=0)
                self.canv.addOutlineEntry(flowable.nav_title, flowable.nav_id, level=0)
    for flowable in story:
        if isinstance(flowable, Paragraph):
            for item in content:
                if flowable.text.startswith('<a name=\"' + item['id'] + '\"/>'):
                    flowable.nav_id = item['id']; flowable.nav_title = item['title']
    document = NavigableDocument(str(path), pagesize=(612, 792), leftMargin=54, rightMargin=54,
                                 topMargin=51, bottomMargin=51, title=packet['title'], author='TJLabs | ZZ-IRIDIUM-Q2B9')
    document.build(story, onFirstPage=footer, onLaterPages=footer, canvasmaker=StableCanvas)


def make_html(packet: dict, content: list[dict]) -> str:
    esc = html.escape
    nav = ''.join(f'<li><a href="#{s["id"]}">{esc(s["title"])}</a></li>' for s in content)
    body = ''.join('<section id="'+s['id']+'"><h2>'+esc(s['title'])+'</h2>' +
                   ''.join('<p>'+esc(plain(t)).replace('\n', '<br>')+'</p>' for t in s['body']) +
                   '<p><a href="#top">Back to contents</a></p></section>' for s in content)
    files = ''.join(f'<li><a href="{name}">{name}</a></li>' for name in FILES if name != FILES[0])
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>'+esc(packet['title'])+'</title><style>body{font:17px/1.55 system-ui,sans-serif;max-width:900px;margin:auto;padding:32px;color:#183749}'
            'a{color:#165a77}a:focus{outline:3px solid}section{border-top:1px solid #bbb;margin-top:35px;padding-top:20px}'
            'p{white-space:normal;overflow-wrap:anywhere}.hold{font-weight:bold;border:2px solid;padding:14px}</style>'
            '<body id="top"><h1>'+esc(packet['title'])+'</h1><p class="hold">'+STATUS+'</p><p>'+NOTICE+'</p>'
            '<p>Open the PDF or DOCX for a paginated review. This HTML contains the complete readable packet without development tools.</p>'
            '<nav aria-label="Contents"><h2>Contents</h2><ol>'+nav+'</ol></nav><h2>Folder files</h2><ul>'+files+'</ul>'+body+'</body></html>')


def check_navigation(folder: Path, content: list[dict]) -> dict:
    import fitz
    from docx import Document
    from docx.oxml.ns import qn
    names = {item['id'] for item in content}
    expected_anchors = [item['id'] for item in content] + [ref for item in content for ref in item['refs']]
    document = Document(folder / '01_REVIEW_DRAFT.docx')
    root = document.element
    bookmarks = [n.get(qn('w:name')) for n in root.iter(qn('w:bookmarkStart'))]
    anchors = [n.get(qn('w:anchor')) for n in root.iter(qn('w:hyperlink'))]
    if set(bookmarks) != names or len(bookmarks) != len(names) or anchors != expected_anchors:
        raise AssemblyError('broken DOCX bookmark/link')
    fields = [n.get(qn('w:instr'), '') for n in root.iter(qn('w:fldSimple'))]
    if [f.split()[1] for f in fields if f.startswith('PAGEREF ')] != expected_anchors:
        raise AssemblyError('DOCX page-reference mismatch')
    target_pages = {item['id']: str(i) for i, item in enumerate(content, 2)}
    for node in root.iter(qn('w:fldSimple')):
        instruction = node.get(qn('w:instr'), '')
        if instruction.startswith('PAGEREF '):
            cached = ''.join(t.text or '' for t in node.iter(qn('w:t')))
            if cached != target_pages[instruction.split()[1]]:
                raise AssemblyError('DOCX cached page-reference mismatch')
    with fitz.open(folder / '01_REVIEW_DRAFT.pdf') as pdf:
        if len(pdf) != len(content) + 1:
            raise AssemblyError(f'PDF pagination overflow: {len(pdf)} pages; regenerate layout')
        outlines = pdf.get_toc()
        if outlines != [[1, item['title'], number] for number, item in enumerate(content, 2)]:
            raise AssemblyError('PDF outline mismatch')
        links = [link for page in pdf for link in page.get_links()]
        if len(links) != len(anchors) or any(link.get('kind') != 1 or link.get('page', -1) not in range(1, len(pdf)) for link in links):
            raise AssemblyError('broken PDF internal navigation')
        for number, item in enumerate(content, 1):
            if item['title'] not in pdf[number].get_text():
                raise AssemblyError('PDF page reference points to wrong section')
        # Check each TOC and each cross-reference against its expected target page.
        expected = [item['id'] for item in content] + [ref for item in content for ref in item['refs']]
        targets = {item['id']: i for i, item in enumerate(content, 1)}
        if [l['page'] for l in links] != [targets[key] for key in expected]:
            raise AssemblyError('PDF cross-reference target mismatch')
        for page in pdf:
            for x0, y0, x1, y1, *rest in page.get_text('blocks'):
                if x0 < 25 or x1 > 587 or y0 < 15 or y1 > 779:
                    raise AssemblyError('PDF text outside page safety bounds')
        pages = len(pdf)
    from html.parser import HTMLParser
    class Links(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids = []; self.links = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if 'id' in attrs: self.ids.append(attrs['id'])
            if tag == 'a': self.links.append(attrs.get('href', ''))
    parser = Links(); parser.feed((folder / FILES[0]).read_text(encoding='utf-8'))
    if len(set(parser.ids)) != len(parser.ids): raise AssemblyError('duplicate HTML anchor')
    expected_links = ['#' + item['id'] for item in content] + [name for name in FILES if name != FILES[0]] + ['#top'] * len(content)
    if parser.links != expected_links: raise AssemblyError('HTML navigation mismatch')
    for target in parser.links:
        if (target.startswith('#') and target[1:] not in parser.ids) or (not target.startswith('#') and target not in FILES):
            raise AssemblyError('broken HTML navigation')
    return {'html_links': len(parser.links), 'pdf_outlines': len(outlines), 'pdf_pages': pages, 'docx_bookmarks': len(bookmarks), 'docx_links': len(anchors), 'pdf_links': len(links)}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')


def build(packet_path: Path, output: Path) -> dict:
    packet, source = load_packet(packet_path)
    content = sections(packet, source)
    output = Path(output).absolute()
    for parent in output.parents:
        if parent.is_symlink(): raise AssemblyError('symlink output parent refused')
    # Exclusive new directory only. Failed builds stay clearly partial; never delete caller data.
    try:
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as exc:
        raise AssemblyError('output must be a new directory under an existing trusted parent') from exc
    (output / 'BUILD_INCOMPLETE.txt').write_text('Incomplete build. Do not submit or distribute.\n')
    (output / FILES[0]).write_text(make_html(packet, content), encoding='utf-8')
    (output / '05_COMMERCIAL_SOURCE.md').write_bytes(source)
    (output / '08_SOURCE_REGISTER.md').write_bytes(read_regular(packet_path.parent / 'source_register.md'))
    for index, name in [(2, '03_FINANCIALS_MISSING.txt'), (3, '04_QUALIFICATIONS_MISSING.txt')]:
        (output / name).write_text(STATUS + '\n\n' + '\n\n'.join(content[index]['body']) + '\n', encoding='utf-8')
    attachments = [{'filename': name, 'status': 'MISSING_PLACEHOLDER' if 'MISSING' in name else 'REVIEW_ARTIFACT'} for name in FILES if name != '07_MANIFEST.json']
    write_json(output / '02_ATTACHMENT_INDEX.json', {'status': STATUS, 'submission_authorized': False, 'attachments': attachments})
    write_json(output / '06_REQUIREMENTS.json', {'edition': 'ORIGINAL; CURRENT AMENDMENT NOT VERIFIED', 'requirements': packet['requirements']})
    make_docx(output / '01_REVIEW_DRAFT.docx', packet, content)
    make_pdf(output / '01_REVIEW_DRAFT.pdf', packet, content)
    navigation = check_navigation(output, content)
    manifest = {'schema': 1, 'status': STATUS, 'submission_authorized': False,
                'source': packet['source'], 'navigation': navigation,
                'visual_review': 'NOT_ESTABLISHED_BY_BUILD',
                'files': {name: digest((output / name).read_bytes()) for name in FILES if name != '07_MANIFEST.json'}}
    write_json(output / '07_MANIFEST.json', manifest)
    (output / 'BUILD_INCOMPLETE.txt').unlink()  # Only our newly created marker in our exclusively created folder.
    return verify(output)


def verify(folder: Path) -> dict:
    folder = Path(folder)
    actual = {p.name for p in folder.iterdir()}
    if actual != set(FILES): raise AssemblyError('output file-set mismatch or incomplete build')
    manifest = strict_json(read_regular(folder / '07_MANIFEST.json').decode('utf-8'))
    expected_keys = {'schema', 'status', 'submission_authorized', 'source', 'navigation', 'visual_review', 'files'}
    if not isinstance(manifest, dict) or set(manifest) != expected_keys or type(manifest['schema']) is not int or manifest['schema'] != 1:
        raise AssemblyError('invalid manifest schema')
    if manifest['status'] != STATUS or manifest['submission_authorized'] is not False:
        raise AssemblyError('invalid or authorizing manifest')
    if set(manifest['files']) != set(FILES) - {'07_MANIFEST.json'}:
        raise AssemblyError('manifest file universe mismatch')
    for name in manifest['files']:
        local_name(name)
        data = read_regular(folder / name)
        if digest(data) != manifest['files'][name]: raise AssemblyError(f'OUTPUT_HASH_MISMATCH: {name}')
        if name.endswith('.json'): strict_json(data.decode('utf-8'))
        elif name.endswith(('.txt', '.md', '.html')): data.decode('utf-8')
    source = read_regular(folder / '05_COMMERCIAL_SOURCE.md')
    if digest(source) != manifest['source']['sha256'] or git_digest(source) != manifest['source']['git_blob_sha']:
        raise AssemblyError('source binding mismatch')
    requirements = strict_json(read_regular(folder / '06_REQUIREMENTS.json').decode('utf-8'))['requirements']
    content = sections({'source': manifest['source'], 'requirements': requirements}, source)
    navigation = check_navigation(folder, content)
    if navigation != manifest['navigation']: raise AssemblyError('navigation receipt mismatch')
    return {'status': 'PACKAGING_INTEGRITY_VERIFIED', 'bid_status': STATUS,
            'submission_authorized': False, **navigation,
            'verified_files': len(FILES), 'visual_review': manifest['visual_review']}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    cmd = sub.add_parser('build'); cmd.add_argument('packet', type=Path); cmd.add_argument('output', type=Path)
    cmd = sub.add_parser('verify'); cmd.add_argument('folder', type=Path)
    args = parser.parse_args(argv)
    try:
        result = build(args.packet, args.output) if args.command == 'build' else verify(args.folder)
    except (AssemblyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f'ASSEMBLY_REFUSED: {exc}', file=sys.stderr); return 2
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
