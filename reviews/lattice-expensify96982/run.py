#!/usr/bin/env python3
"""Restore the exact peer candidate and validate a two-line test-only repair.

Usage: run.py restore|check /path/to/Expensify-App /new/evidence/path
The App checkout must initially contain the pinned upstream base. No remote
branches, production files, locks, snapshots, assertions, or lint baselines
are changed. Commands are serial and all outcomes are retained.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

BASE = '0283d2bebad28796ca74b9506d358232988fe376'
HEAD = '005fae35d28b5d41e517ad9995f476cf02b47168'
BUNDLE_SHA = 'f702c6dbaa10cde1d43b212405e27337aa8a205401ed1523b60064affe4d53f7'
TEST = 'tests/unit/Search/useOptimisticSearchTrackingTest.ts'
SOURCE = 'src/components/Search/hooks/useOptimisticSearchTracking.ts'
SOURCE_SHA = 'b5901942df97f61058aa9c290eddf6b8a0bd9b5c29222d1d57725242bd99b9aa'
TEST_SHA = 'ff32ca5f6f6e6b76745a7969aedef96acdc6aa7abaf8849c0c1d4f80ff885307'
ROOT = Path(__file__).resolve().parent
APP = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []
ENV = dict(os.environ, TZ='UTC', STANDALONE_NEW_DOT='true',
           NODE_OPTIONS='--experimental-vm-modules --max-old-space-size=12288',
           ESLINT_CONCURRENCY='off', SEATBELT_FROZEN='1', SEATBELT_READ_ONLY='1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, label, timeout=600):
    start = time.monotonic()
    try:
        cp = subprocess.run(args, cwd=APP, env=ENV, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        cp = subprocess.CompletedProcess(args, 124, exc.stdout or b'', (exc.stderr or b'') + b'\nTIMEOUT\n')
    (OUT / (label + '.stdout')).write_bytes(cp.stdout)
    (OUT / (label + '.stderr')).write_bytes(cp.stderr)
    print(json.dumps({'command':label,'exit':cp.returncode,'seconds':round(time.monotonic()-start,2)}),flush=True)
    return cp


def must(args, label):
    cp = command(args, label)
    if cp.returncode:
        print(cp.stderr.decode(errors='replace')[-8000:],flush=True)
        raise RuntimeError(label + ' failed')
    return cp


def result(label, passed, **details):
    row = {'check':label,'pass':passed,**details}
    RESULTS.append(row)
    (OUT / 'results.json').write_text(json.dumps(RESULTS,indent=2)+'\n')
    print('RESULT '+json.dumps(row,sort_keys=True),flush=True)


def restore():
    bundle = base64.b64decode((ROOT / 'handoff.bundle.b64').read_text().strip(),validate=True)
    if hashlib.sha256(bundle).hexdigest() != BUNDLE_SHA:
        raise RuntimeError('Handoff bundle SHA256 mismatch')
    target = OUT / 'handoff.bundle'
    target.write_bytes(bundle)
    must(['git','bundle','verify',str(target)],'bundle-verify')
    must(['git','fetch',str(target),'refs/heads/bounty/96982-peer-handoff'],'bundle-fetch')
    must(['git','checkout','--detach',HEAD],'candidate-checkout')
    parent = must(['git','rev-parse','HEAD^'],'candidate-parent').stdout.decode().strip()
    changed = must(['git','diff','--name-only',BASE,HEAD],'candidate-paths').stdout.decode().splitlines()
    if parent != BASE or set(changed) != {TEST,SOURCE}:
        raise RuntimeError('Candidate parent or changed paths mismatch')
    if sha(APP/SOURCE) != SOURCE_SHA or sha(APP/TEST) != TEST_SHA:
        raise RuntimeError('Candidate source bytes differ from final supplement')
    manifest = {'base':BASE,'candidate':HEAD,'bundle_sha256':BUNDLE_SHA,
                'production_sha256':SOURCE_SHA,'test_before_sha256':TEST_SHA,
                'changed_paths':changed,'gate':'No upstream PR before proposal acceptance and hiring; manual account QA not performed.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(APP/TEST,OUT/'test-before.ts')
    (OUT/'candidate.patch').write_bytes(must(['git','diff',BASE,HEAD,'--',SOURCE,TEST],'candidate-diff').stdout)
    for name in ('package.json','package-lock.json'):
        (OUT/(name+'.sha256')).write_text(sha(APP/name)+'\n')
    print('RESTORED '+json.dumps(manifest,sort_keys=True),flush=True)


def typecheck(project, label):
    return command(['node','node_modules/typescript/bin/tsc','--noEmit','--incremental',
                    '--pretty','false','-p',project,'--tsBuildInfoFile',str(OUT/(label+'.tsbuildinfo'))],label)


def check():
    if sha(APP/SOURCE) != SOURCE_SHA or sha(APP/TEST) != TEST_SHA:
        raise RuntimeError('Candidate changed before check')
    for tool in ('node','npm','bun'):
        must([tool,'--version'],'version-'+tool)
    must(['node','node_modules/typescript/bin/tsc','--version'],'version-typescript')
    before = typecheck('tsconfig.jest.json','before-types-jest')
    diagnostics = re.findall(r'(?m)^(.+)\((\d+),(\d+)\): error (TS\d+):',
                             (before.stdout+before.stderr).decode(errors='replace'))
    expected_before = (before.returncode == 1 and len(diagnostics) == 4
                       and {int(d[1]) for d in diagnostics} == {43,93,171,186}
                       and all(d[0].endswith(TEST) and d[3]=='TS2322' for d in diagnostics))
    result('reproduce-four-original-key-type-errors',expected_before,exit=before.returncode,diagnostics=diagnostics)
    path = APP/TEST
    original = path.read_text()
    fixed = original
    for old,new in (
        ('const TRANSACTION_KEY = `${ONYXKEYS.COLLECTION.TRANSACTION}${TRANSACTION_ID}`;',
         'const TRANSACTION_KEY = `${ONYXKEYS.COLLECTION.TRANSACTION}${TRANSACTION_ID}` as const;'),
        ('const nextKey = `${ONYXKEYS.COLLECTION.TRANSACTION}43`;',
         'const nextKey = `${ONYXKEYS.COLLECTION.TRANSACTION}43` as const;')):
        if fixed.count(old) != 1:
            raise RuntimeError('Repair anchor not unique: '+old)
        fixed = fixed.replace(old,new,1)
    path.write_text(fixed)
    result('two-const-assertions-only', fixed.replace('` as const;', '`;') == original,
           test_after_sha256=sha(path), production_unchanged=sha(APP/SOURCE)==SOURCE_SHA)
    (OUT/'repair.patch').write_bytes(must(['git','diff','--',TEST],'repair-diff').stdout)
    shutil.copy2(path,OUT/'test-after.ts')
    for project in ('tsconfig.jest.json','tsconfig.json','tsconfig.bun.json','tsconfig.node.json','server/victory-chart-renderer/tsconfig.json'):
        label = 'after-types-'+project.replace('/','-').replace('.','-')
        cp = typecheck(project,label)
        result(label,cp.returncode==0,exit=cp.returncode)
    selected = sorted(str(p.relative_to(APP)) for p in (APP/'tests/unit').rglob('*.ts')
                      if any(name in p.name for name in ('useOptimisticSearchTracking','useStableOptimisticSortedData','deferredLayoutWrite')))
    if TEST not in selected:
        raise RuntimeError('Changed test is missing from selection')
    (OUT/'selected-tests.json').write_text(json.dumps(selected,indent=2)+'\n')
    cp = command(['node','node_modules/jest/bin/jest.js','--runInBand','--runTestsByPath',*selected,
                  '--json','--outputFile',str(OUT/'jest-results.json')],'focused-jest',timeout=900)
    result('focused-project-jest',cp.returncode==0,exit=cp.returncode,selected=selected)
    cp = command(['bun','scripts/lint.ts','--no-cache','--show-warnings',SOURCE,TEST],'affected-lint',timeout=900)
    result('affected-project-lint',cp.returncode==0,exit=cp.returncode)
    cp = command(['node','node_modules/cspell/bin.mjs','--no-progress',SOURCE,TEST],'affected-spell')
    result('affected-spell',cp.returncode==0,exit=cp.returncode)
    dirty = must(['git','diff','--name-only'],'final-paths').stdout.decode().splitlines()
    result('only-test-file-modified',dirty==[TEST],paths=dirty,production_unchanged=sha(APP/SOURCE)==SOURCE_SHA)
    summary = {'checked':len(RESULTS),'passed':sum(x['pass'] for x in RESULTS),
               'failed':[x['check'] for x in RESULTS if not x['pass']],
               'upstream_submission':False,'manual_account_qa':False}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('SUMMARY '+json.dumps(summary,sort_keys=True),flush=True)
    if summary['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    if sys.argv[1] == 'restore':
        restore()
    elif sys.argv[1] == 'check':
        check()
    else:
        raise SystemExit('mode must be restore or check')
