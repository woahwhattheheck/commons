#!/usr/bin/env python3
"""Independent, real-process CLI/publication review of UIOWA-023/031.

Run with --source pointing at the methodology directory. Source is read and
hashed before execution; every child inherits this interpreter's optimization.
No actual documents, credentials, live systems or assessment claims are used.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import unittest

SOURCES = ('validate_23_evidence_register.py', 'evidence_register_interchange.py',
           'native_031_common_bridge.py')
SOURCE = None
COMMANDS = []

# Executes actual entry points; faults are restricted to temporary-output I/O.
# It does not replace a parser, a validator, a bridge, or its return values.
FAULT_WRAPPER = r'''
import contextlib, errno, os, pathlib, runpy, sys, tempfile
from unittest.mock import patch
fault = sys.argv.pop(1)
script = sys.argv[1]
sys.path.insert(0, str(pathlib.Path(script).resolve().parent))
real_unlink = os.unlink

def cleanup(path, *args, **kwargs):
    if pathlib.Path(path).name.startswith('.uiowa031-'):
        raise PermissionError(errno.EACCES, 'injected temporary cleanup failure')
    return real_unlink(path, *args, **kwargs)

with contextlib.ExitStack() as stack:
    if fault in ('cleanup', 'link-cleanup', 'fsync-cleanup'):
        stack.enter_context(patch.object(os, 'unlink', cleanup))
    if fault in ('link', 'link-cleanup'):
        stack.enter_context(patch.object(os, 'link', side_effect=OSError(errno.EIO, 'injected link failure')))
    if fault in ('fsync', 'fsync-cleanup'):
        stack.enter_context(patch.object(os, 'fsync', side_effect=OSError(errno.ENOSPC, 'injected fsync failure')))
    if fault == 'temporary':
        stack.enter_context(patch.object(tempfile, 'NamedTemporaryFile', side_effect=OSError(errno.ENOSPC, 'injected temporary creation failure')))
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name='__main__')
'''


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def fixture() -> tuple[dict, dict, dict]:
    # Standalone independently authored one-row evidence packet, not GRANITE's
    # original six-document fixture. The reviewed validator checks it normally.
    row = dict(evidence_id='EV-SYN-ESS-SD-ART-001',
               observation_id='OBS-SYN-ESS-SD-001', finding_id='FND-SYN-ESS-SD-001',
               group='ESS', area='SD', source_type='SYNTHETIC_ARTIFACT',
               source_ref='fictional://r53x/example', custodian_or_owner='FICTIONAL OWNER',
               content_digest='sha256:'+'a'*64, captured_at='2026-09-19',
               represented_period='FICTIONAL SNAPSHOT', claim='Synthetic note, not a finding.',
               scope_limit='One invented source only.', directness='DIRECT', recency='UNKNOWN',
               representativeness='SINGLE', corroboration='NO_CORROBORATION',
               evidence_state='SUPPORTING', confidence='LOW', conflict_group='',
               universe_definition='', enumerator_authority='', completeness_basis='',
               follow_up='Seek actual evidence during an authorized engagement.',
               extension='  0007, "quoted"\r\nsecond line\rthird\nλ🧭 =1+1  ')
    common = {'schema': 'uiowa-023-evidence-register/1', 'columns': list(row), 'rows': [row]}
    native = {k:v for k,v in row.items() if k not in ('custodian_or_owner', 'content_digest')}
    native.update(source_id='SRC-SYN-R53X-001', excerpt_locator='lines:1-2', practice_supported='FICTIONAL')
    register = {'columns': list(native), 'rows': [native]}
    doc = dict(source_id='SRC-SYN-R53X-001',title='Fictional source',document_location='not-opened.txt',
               document_version='SYNTHETIC-v1',owner='FICTIONAL OWNER',supplied_date='UNKNOWN',
               source_type='SYNTHETIC_ARTIFACT',sha256='a'*64,retention_note='No real documents retained.')
    manifest = {'columns':list(doc), 'rows':[doc]}
    return common, manifest, register


def csv_text(table: dict) -> str:
    out = io.StringIO(newline='')
    writer=csv.writer(out,lineterminator='\r\n')
    writer.writerow(table['columns'])
    writer.writerows([[row[c] for c in table['columns']] for row in table['rows']])
    return out.getvalue()


def bridge_packet(common: dict, manifest: dict, register: dict) -> dict:
    # Independent oracle, not an invocation of the source under test.
    columns=register['columns']+['custodian_or_owner','content_digest']
    row={**register['rows'][0], 'custodian_or_owner':manifest['rows'][0]['owner'],
         'content_digest':'sha256:'+manifest['rows'][0]['sha256']}
    return {'schema':'uiowa-031-common-register-bridge/1',
            'assessment_authority':False,'document_content_checked':False,
            'source_authenticity_verified':False,'manifest':manifest,
            'native_register_columns':register['columns'],
            'derived_columns':['custodian_or_owner','content_digest'],
            'common_register':{'schema':common['schema'],'columns':columns,'rows':[row]}}


class Boundary(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory(prefix='r53x-boundary-')
        self.root=Path(self.work.name)
        self.addCleanup(self.work.cleanup)
        self.common,self.manifest,self.register=fixture()
        self.bridge=bridge_packet(self.common,self.manifest,self.register)
        self.common_json=self.root/'common.json'; self.common_csv=self.root/'common.csv'
        self.bridge_json=self.root/'bridge.json'; self.native=self.root/'native'; self.native.mkdir()
        self.common_json.write_text(json.dumps(self.common,ensure_ascii=False),encoding='utf-8')
        self.common_csv.write_bytes(csv_text(self.common).encode())
        self.bridge_json.write_text(json.dumps(self.bridge,ensure_ascii=False),encoding='utf-8')
        (self.native/'manifest.csv').write_bytes(csv_text(self.manifest).encode())
        (self.native/'register.csv').write_bytes(csv_text(self.register).encode())
        self.initial={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def invoke(self, command: str, target: Path, *, fault='', input_path=None):
        if command in ('csv-to-json','json-to-csv'):
            script='evidence_register_interchange.py'
            src=self.common_csv if command=='csv-to-json' else self.common_json
        else:
            script='native_031_common_bridge.py'
            src=self.native if command=='import' else self.bridge_json
        src=input_path or src
        argv=[str(SOURCE/script),command,str(src),str(target)]
        opt=['-'+'O'*sys.flags.optimize] if sys.flags.optimize else []
        if fault:
            argv=['-c',FAULT_WRAPPER,fault]+argv
        env=dict(os.environ, PYTHONOPTIMIZE=str(sys.flags.optimize), PYTHONDONTWRITEBYTECODE='1',
                 PYTHONINTMAXSTRDIGITS='4300')
        started=time.monotonic()
        proc=subprocess.run([sys.executable,'-S',*opt,*argv],capture_output=True,text=True,
                            encoding='utf-8',env=env,timeout=15)
        # Normalize only temporary paths in retained logs, not source/output bytes.
        COMMANDS.append({'test':self.id().rsplit('.',1)[-1], 'command':command, 'fault':fault,
                         'optimization':sys.flags.optimize,'no_site':True,'returncode':proc.returncode,
                         'stdout':proc.stdout.replace(str(self.root),'<TMP>'),
                         'stderr':proc.stderr.replace(str(self.root),'<TMP>'),
                         'duration_seconds':round(time.monotonic()-started,6)})
        return proc

    def sources_unchanged(self):
        for rel,data in self.initial.items():
            self.assertEqual((self.root/rel).read_bytes(),data,rel)

    def refused(self, result, output: Path):
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertIn('ERROR:',result.stderr)
        self.assertNotIn('Traceback',result.stderr)
        self.assertNotIn('OK ',result.stdout)
        self.assertFalse(os.path.lexists(output),str(output))
        self.assertEqual(list(self.root.glob('.uiowa031-*')),[])

    def test_success_all_entrypoints(self):
        for command in ENTRYPOINTS:
            with self.subTest(command=command):
                dest=self.root/(command+'.out'); r=self.invoke(command,dest)
                self.assertEqual(r.returncode,0,r.stderr); self.assertIn('OK ',r.stdout)
                self.assertEqual(r.stderr,''); self.assertTrue(dest.is_file())
                if command=='csv-to-json': self.assertEqual(json.loads(dest.read_bytes()),self.common)
                if command=='json-to-csv': self.assertEqual(dest.read_bytes(),csv_text(self.common).encode())
                if command=='import': self.assertEqual(json.loads(dest.read_bytes()),self.bridge)
                if command=='export-manifest': self.assertEqual(dest.read_bytes(),csv_text(self.manifest).encode())
                if command=='export-register': self.assertEqual(dest.read_bytes(),csv_text(self.register).encode())
                if command=='export-common': self.assertEqual(dest.read_bytes(),csv_text(self.bridge['common_register']).encode())
        self.sources_unchanged(); self.assertEqual(list(self.root.glob('.uiowa031-*')),[])

    def test_false_verification_flags_rejected(self):
        for flag in ('assessment_authority','document_content_checked','source_authenticity_verified'):
            for value in (True, 0, 'false', None):
                for command in ('export-common','export-manifest','export-register'):
                    with self.subTest(flag=flag,value=value,command=command):
                        bad=copy.deepcopy(self.bridge); bad[flag]=value
                        inp=self.root/'bad-flags.json'; inp.write_text(json.dumps(bad))
                        dest=self.root/'refused.csv'; r=self.invoke(command,dest,input_path=inp)
                        self.refused(r,dest)
        self.sources_unchanged()

    def test_validator_cli_is_not_verification_authority(self):
        opt=['-'+'O'*sys.flags.optimize] if sys.flags.optimize else []
        proc=subprocess.run([sys.executable,'-S',*opt,str(SOURCE/SOURCES[0]),str(self.common_csv)],
                            capture_output=True,text=True,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(proc.stdout.strip(),'OK rows=1 observations=1 findings=1')
        self.sources_unchanged()

    def test_repeated_valid_publication_does_not_replace(self):
        dest=self.root/'published.json'; a=self.invoke('import',dest)
        self.assertEqual(a.returncode,0,a.stderr); first=dest.read_bytes()
        r=self.invoke('import',dest)
        self.assertEqual(r.returncode,1); self.assertIn('ERROR:',r.stderr)
        self.assertEqual(dest.read_bytes(),first); self.sources_unchanged()


ENTRYPOINTS=('csv-to-json','json-to-csv','import','export-common','export-manifest','export-register')


def alias_test(command, kind):
    def test(self):
        dest=self.root/'held-output'; held=b'EXISTING EVIDENCE\x00\xff\r\n'
        real=self.root/'retained'; real.write_bytes(held)
        if kind=='file': dest.write_bytes(held)
        elif kind=='hardlink': os.link(real,dest)
        elif kind=='symlink': dest.symlink_to(real)
        elif kind=='dangling': dest.symlink_to(self.root/'does-not-exist')
        elif kind=='directory': dest.mkdir(); (dest/'child').write_bytes(held)
        elif kind=='input':
            dest=self.common_csv if command=='csv-to-json' else self.common_json
            if command=='import': dest=self.native/'manifest.csv'
            if command.startswith('export-'): dest=self.bridge_json
            held=dest.read_bytes()
        before_link=os.readlink(dest) if dest.is_symlink() else None
        r=self.invoke(command,dest)
        self.assertEqual(r.returncode,1,r.stderr); self.assertIn('ERROR:',r.stderr)
        self.assertNotIn('Traceback',r.stderr); self.assertNotIn('OK ',r.stdout)
        self.assertEqual(real.read_bytes(),b'EXISTING EVIDENCE\x00\xff\r\n')
        if kind=='directory': self.assertEqual((dest/'child').read_bytes(),held)
        elif kind=='dangling': self.assertEqual(os.readlink(dest),before_link)
        else:self.assertEqual(dest.read_bytes(),held)
        if before_link is not None:self.assertEqual(os.readlink(dest),before_link)
        self.assertEqual(list(self.root.glob('.uiowa031-*')),[]); self.sources_unchanged()
    return test


def malformed_test(command, kind):
    def test(self):
        inp=self.root/'invalid'; dest=self.root/'refused'
        if kind=='missing': pass
        elif kind=='directory': inp.mkdir()
        else:
            data={'utf8':b'\xff\xfe', 'json':'{"unexpected":1}'.encode(),
                  'huge_integer':('{"invalid":'+'1'*5000+'}').encode(),
                  'duplicate_key':b'{"schema":"a","schema":"b"}',
                  'nan':b'{"invalid":NaN}', 'surrogate':b'{"schema":"\\ud800"}',
                  'deep':('['*1200+'0'+']'*1200).encode(),
                  'csv':b'a,a\r\n1,2,3\r\n'}[kind]
            inp.write_bytes(data)
        if command=='import' and kind not in ('missing','directory'):
            packet=self.root/'broken-native';packet.mkdir()
            (packet/'manifest.csv').write_bytes(inp.read_bytes())
            (packet/'register.csv').write_bytes(csv_text(self.register).encode()); inp=packet
        r=self.invoke(command,dest,input_path=inp)
        self.refused(r,dest); self.sources_unchanged()
    return test


def fault_test(command, fault):
    def test(self):
        dest=self.root/'fault-output'; r=self.invoke(command,dest,fault=fault)
        temps=list(self.root.glob('.uiowa031-*'))
        if fault=='cleanup':
            self.assertEqual(r.returncode,0,r.stderr); self.assertIn('OK ',r.stdout)
            self.assertIn('WARNING:',r.stderr); self.assertIn('output published',r.stderr)
            self.assertIn('.uiowa031-',r.stderr);self.assertNotIn('Traceback',r.stderr)
            self.assertTrue(dest.is_file());self.assertEqual(len(temps),1)
            self.assertEqual(dest.read_bytes(),temps[0].read_bytes())
            self.assertEqual(dest.stat().st_ino,temps[0].stat().st_ino)
        elif fault.endswith('-cleanup'):
            self.assertEqual(r.returncode,1,r.stderr);self.assertIn('ERROR:',r.stderr)
            self.assertIn('injected '+fault.split('-')[0]+' failure',r.stderr)
            self.assertIn('cleanup failure',r.stderr);self.assertIn('.uiowa031-',r.stderr)
            self.assertNotIn('Traceback',r.stderr);self.assertNotIn('OK ',r.stdout)
            self.assertFalse(dest.exists());self.assertEqual(len(temps),1)
        else: self.refused(r,dest)
        self.sources_unchanged()
    return test


for command in ENTRYPOINTS:
    for kind in ('file','hardlink','symlink','dangling','directory','input'):
        setattr(Boundary,'test_alias_'+command.replace('-','_')+'_'+kind,alias_test(command,kind))
    kinds=['missing','directory','utf8','csv']
    if command in ('json-to-csv','export-common','export-manifest','export-register'):
        kinds+=['json','huge_integer','duplicate_key','nan','surrogate','deep']
    for kind in kinds:
        setattr(Boundary,'test_invalid_'+command.replace('-','_')+'_'+kind,malformed_test(command,kind))
    for fault in ('temporary','fsync','link','cleanup','link-cleanup','fsync-cleanup'):
        setattr(Boundary,'test_fault_'+command.replace('-','_')+'_'+fault.replace('-','_'),fault_test(command,fault))


def main():
    global SOURCE
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--result',type=Path,required=True)
    ap.add_argument('--source-lock',type=Path)
    ap.add_argument('--part', help='execute one deterministic shard, e.g. 1/4')
    ns=ap.parse_args();SOURCE=ns.source.resolve()
    captured={name:(SOURCE/name).read_bytes() for name in SOURCES}
    hashes={name:{'git_blob':blob(data),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
            for name,data in captured.items()}
    if ns.source_lock:
        wanted=json.loads(ns.source_lock.read_text())
        if {k:v['git_blob'] for k,v in hashes.items()} != wanted:
            raise SystemExit('Source-lock mismatch; no tests executed.')
    output=io.StringIO()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Boundary)
    if ns.part:
        index, count = map(int, ns.part.split('/'))
        if not 1 <= index <= count:
            raise SystemExit('invalid part')
        suite = unittest.TestSuite(t for i,t in enumerate(suite) if i % count == index - 1)
    start=time.monotonic()
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    unchanged=all((SOURCE/name).read_bytes()==data for name,data in captured.items())
    report={'schema':'r53x-cli-boundary-review/1','python':platform.python_version(),
            'platform':platform.platform(),'optimization':sys.flags.optimize,
            'part':ns.part, 'scope':'actual CLI subprocesses and temporary-output I/O injection; not hosted CI or native document validation',
            'tested_source':hashes,'source_unchanged_after_run':unchanged,
            'test_methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'skipped':len(result.skipped),'duration_seconds':round(time.monotonic()-start,6),
            'wrapper_sha256':hashlib.sha256(FAULT_WRAPPER.encode()).hexdigest(),
            'test_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'log':output.getvalue(),'commands':COMMANDS}
    with ns.result.open('x',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(output.getvalue());print('RESULT',ns.result,'source_unchanged',unchanged)
    return 0 if result.wasSuccessful() and unchanged else 1


if __name__=='__main__':raise SystemExit(main())
