"""Bounded synthetic scale exercise; no bank data, network, or performance promise."""
from __future__ import annotations

import argparse
import json
import platform
import resource
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

if __package__:
    from .workbench import write_bundle, verify_bundle
else:
    from workbench import write_bundle, verify_bundle


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--entries', type=int, default=5000)
    args = cli.parse_args()
    if not 1 <= args.entries <= 5000:
        cli.error('--entries must be between 1 and 5000')
    root = ET.fromstring((Path(__file__).parent / 'fixtures/synthetic-v08.xml').read_bytes())
    ns = root.tag[1:].split('}')[0]
    q = lambda name: '{' + ns + '}' + name
    stmt = root.find(q('BkToCstmrStmt')).find(q('Stmt'))
    for child in list(stmt):
        if child.tag in {q('Ntry'), q('TxsSummry')}:
            stmt.remove(child)
    expected_cents = 0
    for i in range(args.entries):
        cents = 200 if i % 2 == 0 else 100
        sign = 'CRDT' if i % 2 == 0 else 'DBIT'
        expected_cents += cents if sign == 'CRDT' else -cents
        fragment = (f'<Ntry xmlns="{ns}"><NtryRef>SCALE-{i}</NtryRef>'
                    f'<Amt Ccy="GBP">{cents // 100}.00</Amt><CdtDbtInd>{sign}</CdtDbtInd>'
                    '<Sts><Cd>BOOK</Cd></Sts><BookgDt><Dt>2026-09-17</Dt></BookgDt>'
                    f'<AcctSvcrRef>SYNTHETIC-{i}</AcctSvcrRef>'
                    '<BkTxCd><Prtry><Cd>SCALE_ONLY</Cd></Prtry></BkTxCd></Ntry>')
        stmt.append(ET.fromstring(fragment))
    for bal in stmt.findall(q('Bal')):
        if bal.find(q('Tp')).find(q('CdOrPrtry')).find(q('Cd')).text == 'CLBD':
            bal.find(q('Amt')).text = f'{(100000 + expected_cents) // 100}.00'
    raw = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    with tempfile.TemporaryDirectory() as parent:
        target = Path(parent) / 'new-review'
        started = time.perf_counter()
        report = write_bundle({'synthetic-scale.xml': raw}, target)
        built = time.perf_counter()
        verified = verify_bundle(target)
        stopped = time.perf_counter()
        check = report['statements'][0]['balance_checks'][0]
        if (report['status'] != 'EXTRACTED' or report != verified or
                report['counts']['entries'] != args.entries or
                check['result'] != 'ARITHMETIC_MATCH' or
                check['booked_entries_net'] != str(expected_cents // 100)):
            raise RuntimeError('synthetic integer-oracle mismatch')
        print(json.dumps({'python': platform.python_version(), 'platform': platform.platform(),
                          'entries': args.entries, 'source_bytes': len(raw),
                          'bundle_bytes': sum(p.stat().st_size for p in target.rglob('*') if p.is_file()),
                          'build_seconds': round(built-started, 6),
                          'verify_seconds': round(stopped-built, 6),
                          'peak_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          'result': 'PASS', 'booked_entries_net': check['booked_entries_net']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
