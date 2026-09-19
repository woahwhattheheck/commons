#!/usr/bin/env python3
"""Offline evidence reconciliation and portable case review.

Reconstructed from Z-Quorum-7F2C's retained #15959 contract. This does not
perform underwriting, affordability, eligibility, fraud or lending decisions.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import mortgage_core as core

ContractError = core.ContractError
normalize_case = core.normalize_case
compile_case = core.compile_case
canonical_bytes = core.canonical_bytes
MAX_INPUT_BYTES = 2_000_000
MAX_RECEIPT_BYTES = 32_000_000
BUNDLE_SCHEMA = 'mortgage-case-bundle/v1'
ROOT = Path(__file__).resolve().parent
_SOURCE_BYTES = {name: (ROOT / name).read_bytes() for name in ('mortgage_core.py', 'mortgage_case_reconcile.py')}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json_bytes(data: bytes, *, max_bytes: int = MAX_INPUT_BYTES):
    if len(data) > max_bytes:
        raise ContractError(f'JSON input exceeds {max_bytes:,} bytes')
    try:
        return core.strict_json_loads(data.decode('utf-8'))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ContractError(f'invalid UTF-8 JSON: {exc}') from exc


def load_json(path: str | Path, *, max_bytes: int = MAX_INPUT_BYTES):
    try:
        return load_json_bytes(Path(path).read_bytes(), max_bytes=max_bytes)
    except OSError as exc:
        raise ContractError(f'cannot read JSON input: {exc}') from exc


def verify_receipt(raw_case, receipt) -> dict:
    expected = compile_case(raw_case)
    try:
        if canonical_bytes(receipt) != canonical_bytes(expected):
            raise ContractError('receipt differs from a fresh compilation of the supplied case')
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError(f'invalid receipt or compilation mismatch: {exc}') from exc
    return {'ok': True, 'case_id': expected['case_id'], 'source_digest': expected['source_digest'],
            'semantic_digest': expected['semantic_digest']}


def _text(value) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _cell(value) -> str:
    text = _text(value)
    # CSV consumers may otherwise evaluate leading formula characters.
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def exception_csv(receipt: dict) -> str:
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['case_id', 'issue_id', 'code', 'subject', 'severity', 'source_ids', 'details', 'action_ids', 'next_actions'])
    actions = {}
    for action in receipt['next_actions']:
        actions.setdefault(action['issue_id'], []).append(action)
    for issue in receipt['issues']:
        linked = actions.get(issue['issue_id'], [])
        row = [receipt['case_id'], issue['issue_id'], issue['code'], issue['subject'], issue['severity'],
               '; '.join(issue['source_ids']), issue['details'], '; '.join(a['action_id'] for a in linked),
               '; '.join(a['action'] for a in linked)]
        writer.writerow([_cell(value) for value in row])
    return output.getvalue()


def _e(value) -> str:
    return html.escape(_text(value), quote=True)


def _download(name: str, raw: bytes, label: str) -> str:
    encoded = base64.b64encode(raw).decode('ascii')
    return f'<a download="{name}" href="data:application/octet-stream;base64,{encoded}">{_e(label)}</a>'


_SCRIPT = """const search = document.getElementById('search');
const code = document.getElementById('issue-code');
const cards = Array.from(document.querySelectorAll('.issue'));
function applyFilters() {
 const query = search.value.toLocaleLowerCase().trim();
 let visible = 0;
 for (const card of cards) {
  const show = (!code.value || card.dataset.code === code.value) && (!query || card.dataset.search.toLocaleLowerCase().includes(query));
  card.hidden = !show;
  if (show) visible += 1;
 }
 document.getElementById('issue-count').textContent = visible + ' of ' + cards.length + ' exceptions';
}
search.addEventListener('input', applyFilters);
code.addEventListener('change', applyFilters);
applyFilters();"""
_STYLE = """*{box-sizing:border-box}body{margin:0;font:16px/1.5 system-ui,sans-serif;color:#21313d;background:#f4f2ec}header{padding:2.5rem max(5vw,1rem);background:#233d4b;color:#fff}header p{max-width:85ch}h1{font-size:clamp(2rem,5vw,3.2rem);line-height:1.1;margin:.5em 0}h2{margin-top:2.2rem}h3{margin:.3rem 0}.eyebrow{text-transform:uppercase;font-size:.8rem;letter-spacing:.15em}.chips,nav,.downloads,.controls{display:flex;flex-wrap:wrap;gap:1rem}.chip{background:#e5b773;color:#322313;padding:.35rem .7rem;border-radius:4px}.clear{background:#b8d6be;color:#173c25}main{max-width:1200px;margin:auto;padding:1.5rem 1rem}a{color:#175273;text-underline-offset:.2em}header a{color:#e0eef8}section{scroll-margin-top:1rem}.notice{background:#e8e4d7;padding:1rem;border-radius:5px}.issue,details{padding:1.1rem;margin:1rem 0;background:#fff;border:1px solid #cecdbf;border-radius:6px}.issue{border-left:5px solid #ac7130}.issue[hidden]{display:none}.controls label{display:flex;flex-direction:column;gap:.4rem}input,select{font:inherit;padding:.65rem;border:1px solid #90999e;border-radius:4px;max-width:100%}input{width:min(28rem,85vw)}table{width:100%;border-collapse:collapse;font-size:.9rem}th,td{text-align:left;border-bottom:1px solid #d9dfdf;padding:.6rem;vertical-align:top;overflow-wrap:anywhere}th{background:#e9edee}.table-wrap{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f4;padding:.7rem;border-radius:3px}code{overflow-wrap:anywhere}summary{cursor:pointer;font-weight:650}.small{font-size:.83rem;color:#53666e}.downloads a{border:1px solid #798f98;border-radius:4px;padding:.45rem .7rem}.value{font-family:ui-monospace,monospace}footer{margin-top:2rem;border-top:1px solid #c5cccb;padding-top:1rem}@media print{.controls,.downloads{display:none}.issue[hidden]{display:block}body{background:#fff}header{background:#fff;color:#21313d}.issue{break-inside:avoid}}"""


def html_summary(receipt: dict) -> str:
    actions = {}
    for action in receipt['next_actions']:
        actions.setdefault(action['issue_id'], []).append(action)
    issue_cards = []
    for issue in receipt['issues']:
        linked = actions.get(issue['issue_id'], [])
        steps = ''.join(f'<li><code>{_e(a["action_id"])}</code> — {_e(a["action"])}</li>' for a in linked)
        issue_cards.append(f'<article class="issue" id="{_e(issue["issue_id"])}" data-code="{_e(issue["code"])}" data-search="{_e(issue)}">'
                           f'<span class="small">{_e(issue["issue_id"])} · {_e(issue["severity"])}</span><h3>{_e(issue["code"])}</h3>'
                           f'<p><strong>{_e(issue["subject"])}</strong> · Sources: {_e(issue["source_ids"])}</p><pre>{_e(issue["details"])}</pre>'
                           f'<p><strong>Recorded review action</strong></p><ul>{steps or "<li>No action recorded.</li>"}</ul></article>')
    fields = []
    for field in receipt['fields']:
        rows = ''.join('<tr>'+''.join(f'<td>{_e(value)}</td>' for value in (ob['source_id'],ob['observed_at'],ob['required'],ob['value']))+'</tr>' for ob in field['observations'])
        fields.append(f'<details><summary>{_e(field["field_id"])} — {_e(field["status"])}</summary><p>Kind: {_e(field["kind"])}. Required sources: {_e(field["required_sources"])}. Missing: {_e(field["missing_sources"])}</p>'
                      f'<div class="table-wrap"><table><thead><tr><th>Source</th><th>Observed</th><th>Required</th><th>Normalized value</th></tr></thead><tbody>{rows}</tbody></table></div></details>')
    documents = []
    for doc in receipt['documents']:
        rows = ''.join('<tr>'+''.join(f'<td>{_e(value)}</td>' for value in (ob['source_id'],ob['document_id'],ob['sha256'],ob['status'],ob['observed_at']))+'</tr>' for ob in doc['observations'])
        documents.append(f'<details><summary>{_e(doc["document_type"])} — {_e(doc["status"])}</summary>'
                         f'<p>Required: {_e(doc["required"])} · Minimum distinct validated hashes: {_e(doc["min_validated"])}</p>'
                         f'<p>Uncontested validated hashes: {_e(doc["validated_unique_hashes"])}<br>Contested hashes: {_e(doc["contested_hashes"])}</p>'
                         f'<div class="table-wrap"><table><thead><tr><th>Source</th><th>Document ID</th><th>Declared SHA-256</th><th>Declared status</th><th>Observed</th></tr></thead><tbody>{rows}</tbody></table></div></details>')
    timeline = ''.join('<tr>'+''.join(f'<td>{_e(event[k])}</td>' for k in ('at','event_id','event_type','milestone','channel','message_ref'))+'</tr>' for event in receipt['timeline'])
    groups = ''.join(f'<details><summary>Status observation group {i}</summary><pre>{_e(group)}</pre></details>' for i,group in enumerate(receipt['status_groups'],1))
    codes = ''.join(f'<option value="{_e(code)}">{_e(code)}</option>' for code in sorted({issue['code'] for issue in receipt['issues']}))
    downloads = ''.join((_download('receipt.json',canonical_bytes(receipt)+b'\n','Receipt JSON'),
                         _download('normalized-case.json',canonical_bytes(receipt['case'])+b'\n','Normalized case JSON'),
                         _download('exceptions.csv',exception_csv(receipt).encode('utf-8'),'Exception CSV')))
    script_hash = base64.b64encode(hashlib.sha256(_SCRIPT.encode()).digest()).decode('ascii')
    csp = f"default-src 'none'; script-src 'sha256-{script_hash}'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'"
    clear = receipt['reconciliation_status'] == 'NO_DECLARED_BLOCKERS'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="{html.escape(csp,quote=True)}"><title>Case evidence review · {_e(receipt['case_id'])}</title><style>{_STYLE}</style></head>
<body><header><div class="eyebrow">Mortgage case / supplied evidence review</div><h1>{_e(receipt['case_id'])}</h1><p>Compare the records. Keep disagreements visible. Retain the evidence behind the next review step.</p><div class="chips"><span class="chip{' clear' if clear else ''}">{_e(receipt['reconciliation_status'])}</span><span class="chip">{len(receipt['issues'])} exceptions</span><span class="chip">{len(receipt['case']['sources'])} supplied sources</span></div><p>Subject reference: {_e(receipt['subject_ref'])} · assessed as of {_e(receipt['as_of'])}<br>Recorded milestone: {_e(receipt['current_milestone'])} · {_e(receipt['current_milestone_status'])}</p><nav><a href="#exceptions">Exceptions</a><a href="#fields">Field evidence</a><a href="#documents">Documents</a><a href="#history">History</a></nav></header>
<main><p class="notice">This is offline reconciliation of supplied records. No declared blockers is not lending approval, eligibility, affordability, fraud clearance or authority to act. Document hashes and validation labels are supplied observations; document contents were not inspected. This page makes no network requests.</p><div class="downloads">{downloads}</div><p class="small">Money values remain currency codes and integer minor units. The currency code's precision or validity is not inferred. The normalized case differs from the original JSON representation, which the full packet preserves separately.</p>
<section id="exceptions"><h2>Review exceptions</h2><div class="controls"><label>Search exceptions<input id="search" type="search" placeholder="Field, document, source or issue…"></label><label>Issue code<select id="issue-code"><option value="">All codes</option>{codes}</select></label><p id="issue-count" role="status" aria-live="polite">{len(issue_cards)} of {len(issue_cards)} exceptions</p></div><noscript><p>All records remain available without JavaScript. Filtering requires JavaScript.</p></noscript>{''.join(issue_cards) or '<p>No declared reconciliation blockers were found in this supplied case.</p>'}</section>
<section id="fields"><h2>Cross-system field evidence</h2><p>Every supplied observation remains visible, including optional sources. Missing required observations and disagreements are separate findings.</p>{''.join(fields)}</section>
<section id="documents"><h2>Declared document evidence</h2><p>Repeated copies of one hash count once. Contradictory statuses or document identities remain review issues.</p>{''.join(documents)}</section>
<section id="history"><h2>Recorded event history</h2><p>Only status events establish milestone state. Requests, responses and document events remain context. Simultaneous conflicting status observations are explicit ambiguity.</p><div class="table-wrap"><table><thead><tr><th>Time</th><th>Event</th><th>Type</th><th>Milestone</th><th>Channel</th><th>Reference</th></tr></thead><tbody>{timeline}</tbody></table></div>{groups}</section>
<footer><h2>Reproduction and scope</h2><p class="small">Normalized source digest: <code>{_e(receipt['source_digest'])}</code><br>Semantic receipt digest: <code>{_e(receipt['semantic_digest'])}</code></p><details><summary>Authority fields</summary><pre>{_e(receipt['authority'])}</pre></details><p class="small">Unsigned digests support reproduction, not source authentication. Original contract: Z-Quorum-7F2C. Reviewed reconstruction: ZZ–Trellis and collaborating Codex agents.</p></footer></main><script>{_SCRIPT}</script></body></html>
'''


def _source_copies() -> dict[str, bytes]:
    for name, raw in _SOURCE_BYTES.items():
        if (ROOT/name).read_bytes() != raw:
            raise ContractError(f'support source changed since import: {name}')
    return dict(_SOURCE_BYTES)


def _payloads(raw: bytes) -> tuple[dict[str, bytes], dict]:
    supplied = load_json_bytes(raw)
    receipt = compile_case(supplied)
    payloads = {'case.json':raw,'normalized-case.json':canonical_bytes(receipt['case'])+b'\n',
                'receipt.json':canonical_bytes(receipt)+b'\n','exceptions.csv':exception_csv(receipt).encode('utf-8'),
                'summary.html':html_summary(receipt).encode('utf-8')}
    payloads.update(_source_copies())
    payloads['README.md'] = b'''# Portable supplied-case review

Open summary.html directly in a browser. It retains the complete observations, exception/action links and downloadable normalized case, receipt and CSV. No server or network is required.

From this directory, with Python 3.11 or newer:

```sh
python -B mortgage_case_reconcile.py verify-bundle .
```

Only execute source you trust. Verification regenerates the normalized case, receipt, CSV and HTML from exact case.json bytes and compares the full payload inventory and support source. Unsigned hashes are not authentication or arbitrary-interpreter attestation.

This packet is offline evidence reconciliation. It makes no lending, eligibility, affordability, fraud or compliance determination, authorizes no external action, and does not verify document contents. The input's actual source classification is not inferred.

Export to a new directory for every revision. Keep earlier packets to inspect earlier disagreements. A fresh write failure can leave an incomplete directory; bundle-manifest.json is written last and verification is required before treating the packet as complete.
'''
    return payloads,receipt


def _manifest(payloads, receipt) -> dict:
    return {'schema':BUNDLE_SCHEMA,'case_id':receipt['case_id'],'source_digest':receipt['source_digest'],
            'semantic_digest':receipt['semantic_digest'],'input_sha256':_sha(payloads['case.json']),
            'files':{name:_sha(raw) for name,raw in sorted(payloads.items())}}


def _ok(receipt: dict) -> dict:
    return {'ok':True,'case_id':receipt['case_id'],'source_digest':receipt['source_digest'],'semantic_digest':receipt['semantic_digest']}


def export_bundle(input_path: str | Path, output_dir: str | Path) -> dict:
    root=Path(output_dir)
    try:
        raw=Path(input_path).read_bytes()
        payloads,receipt=_payloads(raw)
        manifest=_manifest(payloads,receipt)
        root.mkdir(exist_ok=False)
        for name,data in payloads.items():
            with (root/name).open('xb') as stream:
                stream.write(data)
        with (root/'bundle-manifest.json').open('xb') as stream:
            stream.write(canonical_bytes(manifest)+b'\n')
        return _ok(receipt)
    except OSError as exc:
        raise ContractError(f'bundle publication failed; existing destinations are preserved: {exc}') from exc


def verify_bundle(output_dir: str | Path) -> dict:
    root=Path(output_dir)
    try:
        if root.is_symlink() or not root.is_dir():
            raise ContractError('bundle must be a regular directory')
        entries=list(root.iterdir())
        if any(p.is_symlink() or not p.is_file() for p in entries):
            raise ContractError('bundle must contain only regular payload files')
        manifest=load_json_bytes((root/'bundle-manifest.json').read_bytes())
        expected,receipt=_payloads((root/'case.json').read_bytes())
        if {p.name for p in entries} != set(expected)|{'bundle-manifest.json'}:
            raise ContractError('bundle file inventory mismatch')
        if canonical_bytes(manifest)!=canonical_bytes(_manifest(expected,receipt)):
            raise ContractError('bundle receipt does not match reproduced payloads')
        for name,raw in expected.items():
            if (root/name).read_bytes()!=raw:
                raise ContractError(f'bundle payload differs from reproduction: {name}')
        return _ok(receipt)
    except (OSError,TypeError,ValueError,UnicodeError,RecursionError) as exc:
        raise ContractError(f'cannot verify bundle: {exc}') from exc


def _compile_paths(input_path: Path, paths: list[Path]) -> dict:
    raw=input_path.read_bytes()
    receipt=compile_case(load_json_bytes(raw))
    destinations=[p.resolve() for p in paths]
    if len(set(destinations))!=3 or input_path.resolve() in destinations:
        raise ContractError('input and export paths must be distinct')
    for path in paths:
        if path.exists() or path.is_symlink():
            raise ContractError(f'export destination already exists: {path}')
        if not path.parent.is_dir():
            raise ContractError(f'export parent directory does not exist: {path.parent}')
    data=[canonical_bytes(receipt)+b'\n',exception_csv(receipt).encode('utf-8'),html_summary(receipt).encode('utf-8')]
    for path,content in zip(paths,data):
        with path.open('xb') as stream:
            stream.write(content)
    return _ok(receipt)


def main(argv: list[str]|None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    compile_parser=commands.add_parser('compile')
    compile_parser.add_argument('input',type=Path)
    for name in ('json','csv','html'):
        compile_parser.add_argument('--'+name+'-out',type=Path,required=True)
    verify=commands.add_parser('verify');verify.add_argument('input',type=Path);verify.add_argument('receipt',type=Path)
    bundle=commands.add_parser('bundle');bundle.add_argument('input',type=Path);bundle.add_argument('--output-dir',type=Path,required=True)
    check=commands.add_parser('verify-bundle');check.add_argument('output_dir',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=='compile':result=_compile_paths(args.input,[args.json_out,args.csv_out,args.html_out])
        elif args.command=='verify':result=verify_receipt(load_json(args.input),load_json(args.receipt,max_bytes=MAX_RECEIPT_BYTES))
        elif args.command=='bundle':result=export_bundle(args.input,args.output_dir)
        else:result=verify_bundle(args.output_dir)
    except (OSError,ContractError,UnicodeError,RecursionError) as exc:
        parser.exit(2,f'mortgage reconciliation: {exc}\n')
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
