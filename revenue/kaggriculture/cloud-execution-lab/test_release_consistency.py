# SPDX-License-Identifier: Apache-2.0
"""Discriminating release tests; no game panel."""
import hashlib,json,shutil,subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
import build_integrated as b

class ReleaseTests(unittest.TestCase):
 def test_default_build_and_history_preservation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'cloud-execution-lab';root.mkdir()
   for p in set(b.source_files().values())|{'build_integrated.py',b.RECORD+'RELEASE.json'}:
    dest=root/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(b.ROOT/p,dest)
   (root/'exports').mkdir();old=b'historical evidence sentinel';(root/b.ARCHIVE).write_bytes(old)
   named=root/'exports/integrated-selected-v1.tar.gz';named.write_bytes(b'unchanged control')
   def call(*args):return subprocess.run([sys.executable,str(root/'build_integrated.py'),*args],capture_output=True,text=True)
   out=call();self.assertEqual(out.returncode,0,out.stderr)
   receipt=json.loads(out.stdout);self.assertEqual(receipt['path'],b.ARCHIVE)
   self.assertEqual(named.read_bytes(),b'unchanged control')
   self.assertEqual((root/'exports/historical'/('titan-'+hashlib.sha256(old).hexdigest()+'.tar.gz')).read_bytes(),old)
   with tarfile.open(root/b.ARCHIVE) as t:
    self.assertEqual(t.extractfile('main.py').read(),(b.ROOT/'main.py').read_bytes())
    manifest=json.load(t.extractfile('SOURCE.json'))
    for name,row in manifest['runtime'].items():
     self.assertEqual(t.extractfile(name).read(),(root/row['source_path']).read_bytes())
    self.assertIn('terminal_history_join.py',t.getnames())
    self.assertIn('funded_payback.py',t.getnames())
    self.assertIn('seed_retry.py',t.getnames())
    self.assertIn('early_capital.py',t.getnames())
    self.assertIn('checks/test_early_capital.py',t.getnames())
    self.assertEqual(manifest['runtime']['seed_retry.py']['source_path'],
                     '../cloud-committed-seed-retry/seed_retry.py')
    self.assertTrue(any(p.startswith('reference/titan-history/') for p in t.getnames()))
    self.assertNotIn('integrated_main.py',t.getnames())
   first=(root/b.ARCHIVE).read_bytes();self.assertEqual(call().returncode,0);self.assertEqual(first,(root/b.ARCHIVE).read_bytes())
   for target in ['main.py','TITAN-CONFIG.json',b.RECORD+'CURRENT-SOURCE.json',b.RECORD+'CURRENT-ARCHIVE.json',b.ARCHIVE,'reference/titan-history/selected_action_history.py']:
    p=root/target;original=p.read_bytes()
    if target.endswith('CURRENT-ARCHIVE.json'):
     changed=json.loads(original);changed['path']='exports/integrated-selected-v1.tar.gz';p.write_text(json.dumps(changed))
    else:p.write_bytes(original+b' ')
    self.assertNotEqual(call('--check').returncode,0,target)
    p.write_bytes(original)
   self.assertEqual(call('--check').returncode,0)
   for flag in ['--history-v2','--entry-clock-v3','--version']:
    self.assertNotEqual(call(flag).returncode,0)

 def test_live_current_includes_early_capital(self):
  receipt=b.verify_current()
  self.assertEqual(receipt['path'],b.ARCHIVE)
  with tarfile.open(b.ROOT/b.ARCHIVE) as t:
   regular=[m.name for m in t.getmembers() if m.isfile()]
   names=t.getnames()
   self.assertEqual(receipt['runtime_files'], len(regular))
   self.assertIn('SOURCE.json', regular)
   self.assertIn('early_capital.py',names)
   self.assertIn('checks/test_early_capital.py',names)
   self.assertIn('checks/test_final_market_pressure_entrypoint.py',names)
   self.assertIn('checks/test_entrypoint_deadline.py',names)
   config=json.load(t.extractfile('TITAN-CONFIG.json'))
   self.assertTrue(config.get('early_capital'))
   self.assertIn(b'def _early_capital_selected',t.extractfile('titan_runtime.py').read())
   main=t.extractfile('main.py').read()
   self.assertEqual(main,(b.ROOT/'main.py').read_bytes())
   self.assertIn(b'class FinalPressureAgent',main)
   self.assertIn(b'_final_pressure_boundary',main)
   self.assertIn(b'def _entrypoint_fallback',main)
   self.assertIn(b'entrypoint_guard',main)

if __name__=='__main__':unittest.main()