from __future__ import annotations
import argparse, json
from pathlib import Path
from .core import BrokerError, compile_current, loads_strict_json, verify_current, verify_integrity

def _read(path): return loads_strict_json(Path(path).read_bytes())
def _write_x(path,obj):
    data=json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n'
    with open(path,'x',encoding='utf-8',newline='\n') as f: f.write(data)

def main(argv=None):
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd',required=True)
    c=s.add_parser('compile'); c.add_argument('packet'); c.add_argument('--out',required=True)
    for name in ('verify-integrity','verify-current'):
        q=s.add_parser(name); q.add_argument('packet'); q.add_argument('receipt')
    a=p.parse_args(argv)
    try:
        if a.cmd=='compile': _write_x(a.out,compile_current(_read(a.packet))); return 0
        ok=(verify_integrity if a.cmd=='verify-integrity' else verify_current)(_read(a.packet),_read(a.receipt))
        print('VALID' if ok else 'INVALID'); return 0 if ok else 1
    except (BrokerError,OSError) as e:
        print(f'ERROR: {e}'); return 2
if __name__=='__main__': raise SystemExit(main())
