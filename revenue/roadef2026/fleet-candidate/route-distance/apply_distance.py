#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply only the exact distance-method insertion and update its manifest row.

This developer utility deliberately refuses unknown distance edits. Other solver
regions and manifest entries are retained, so independent topology/objective
changes can be composed without replacing the full file from an old snapshot.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from probe import extract

HERE=Path(__file__).resolve().parent

def apply(source: bytes) -> bytes:
    text=source.decode('utf-8')
    method=extract(text)
    original=(HERE/'distance_original.inc').read_text()
    candidate=original.replace('        if (a == b) return 0;\n',
        '        if (a == b) return 0;\n'+(HERE/'fast_path.inc').read_text(),1)
    if method==candidate:
        return source
    if method!=original:
        raise ValueError('distance has independent edits; compose the method explicitly')
    return text.replace(original.rstrip('\n'),candidate.rstrip('\n'),1).encode('utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--manifest-output',type=Path)
    args=parser.parse_args()
    if bool(args.manifest)!=bool(args.manifest_output):
        parser.error('manifest and manifest-output must be supplied together')
    original=args.source.read_bytes()
    result=apply(original)
    manifest=None
    if args.manifest:
        manifest=json.loads(args.manifest.read_text())
        rows=[r for r in manifest['files'] if r['path']=='main.cpp']
        if len(rows)!=1:
            raise ValueError('Expected exactly one main.cpp manifest row')
        entry=rows[0]
        expected=hashlib.sha256(original).hexdigest()
        if entry['bytes']!=len(original) or entry['sha256']!=expected:
            raise ValueError('Input manifest does not match the source bytes')
        entry.update(bytes=len(result),sha256=hashlib.sha256(result).hexdigest())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(result)
    if manifest is not None:
        args.manifest_output.parent.mkdir(parents=True,exist_ok=True)
        args.manifest_output.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'before_sha256':hashlib.sha256(original).hexdigest(),
                      'after_sha256':hashlib.sha256(result).hexdigest(),
                      'bytes':len(result),'changed':result!=original}))

if __name__=='__main__':main()
