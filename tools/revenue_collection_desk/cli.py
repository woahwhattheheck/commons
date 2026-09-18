from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .core import CollectionError, publish_bundle, read_regular, verify_bundle

def main(argv=None):
 p=argparse.ArgumentParser(prog='revenue-collection-desk'); s=p.add_subparsers(dest='command',required=True)
 for name in ('compile','verify'):
  q=s.add_parser(name); q.add_argument('source',type=Path); q.add_argument('output',type=Path)
 a=p.parse_args(argv)
 try:
  raw=read_regular(a.source)
  if a.command=='compile':
   out=publish_bundle(raw,a.output); print(json.dumps({'ok':True,'artifacts':sorted(out)},sort_keys=True,separators=(',',':')))
  else:
   verify_bundle(raw,a.output); print('{"ok":true,"verified":true}')
  return 0
 except (CollectionError,OSError,FileExistsError) as e:
  print(json.dumps({'ok':False,'error':str(e)},sort_keys=True,separators=(',',':')),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
