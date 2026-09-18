import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from tools.repo_portability.repo_portability import *
ROOT=Path(__file__).resolve().parents[1]; TOOL=ROOT/'tools/repo_portability/repo_portability.py'
def rg(repo,*a):
 p=subprocess.run(['git',*a],cwd=repo,text=True,capture_output=True); assert p.returncode==0,p.stderr; return p.stdout.strip()
def inv(rows):return {'schema':INVENTORY_SCHEMA,'repositories':rows}
def row(repository='acme/demo',action='KEEP_PRIVATE',local_path=None,source_url=None,destination_url=None):return {'repository':repository,'action':action,'local_path':local_path,'source_url':source_url,'destination_url':destination_url}
class Repo(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.b=Path(self.t.name);self.r=self.b/'src';self.r.mkdir();rg(self.r,'init','-b','main');rg(self.r,'config','user.name','T');rg(self.r,'config','user.email','t@example.invalid');(self.r/'a').write_text('a\n');rg(self.r,'add','a');env=dict(os.environ,GIT_AUTHOR_DATE='2026-01-01T00:00:00Z',GIT_COMMITTER_DATE='2026-01-01T00:00:00Z');p=subprocess.run(['git','commit','-m','a'],cwd=self.r,text=True,capture_output=True,env=env);self.assertEqual(p.returncode,0,p.stderr);rg(self.r,'branch','feature');rg(self.r,'tag','v1');rg(self.r,'update-ref','refs/meta/checkpoint',rg(self.r,'rev-parse','HEAD'))
 def tearDown(self):self.t.cleanup()
class Snapshot(Repo):
 def test_roundtrip(self):
  x=snapshot(self.r,self.b/'out');self.assertEqual((x['state'],x['fsck']),('VERIFIED_RESTORABLE','PASS'));self.assertGreaterEqual(x['ref_count'],5);self.assertEqual(x['authority'],AUTHORITY);self.assertEqual(verify_snapshot(self.b/'out/manifest.json')['bundle_sha256'],x['bundle_sha256']);d=json.loads((self.b/'out/manifest.json').read_text());self.assertNotIn('source',d);self.assertNotIn('created_at',d)
 def test_detached(self):
  h=rg(self.r,'rev-parse','HEAD');rg(self.r,'checkout','--detach',h);self.assertIsNone(snapshot(self.r,self.b/'out')['head_ref'])
 def test_existing_output(self):
  (self.b/'out').mkdir();self.assertRaises(PortabilityError,snapshot,self.r,self.b/'out')
 def test_tamper(self):
  snapshot(self.r,self.b/'out');f=open(self.b/'out/repo.bundle','ab');f.write(b'x');f.close();self.assertRaises(PortabilityError,verify_snapshot,self.b/'out/manifest.json')
 def test_manifest_authority(self):
  snapshot(self.r,self.b/'out');p=self.b/'out/manifest.json';d=json.loads(p.read_text());d['authority']['delete_authorized']=True;p.write_bytes(canon(d));self.assertRaises(PortabilityError,verify_snapshot,p)
 def test_symlinks(self):
  if not hasattr(os,'symlink'):self.skipTest('no symlink')
  snapshot(self.r,self.b/'out');m=self.b/'m';m.symlink_to(self.b/'out/manifest.json');self.assertRaises(PortabilityError,verify_snapshot,m);real=self.b/'out/real';(self.b/'out/repo.bundle').rename(real);(self.b/'out/repo.bundle').symlink_to(real);self.assertRaises(PortabilityError,verify_snapshot,self.b/'out/manifest.json')
 def test_source_symlink(self):
  l=self.b/'link';l.symlink_to(self.r,target_is_directory=True);self.assertRaises(PortabilityError,snapshot,l,self.b/'out')
 def test_cli(self):
  out=self.b/'out';opt=['-O'] if sys.flags.optimize else [];p=subprocess.run([sys.executable,*opt,str(TOOL),'snapshot','--source',str(self.r),'--output-dir',str(out)],cwd=ROOT,text=True,capture_output=True);self.assertEqual(p.returncode,0,p.stderr);q=subprocess.run([sys.executable,*opt,str(TOOL),'verify','--manifest',str(out/'manifest.json')],cwd=ROOT,text=True,capture_output=True);self.assertEqual(q.returncode,0,q.stderr)
class Json(unittest.TestCase):
 def test_strict(self):
  for b in (b'{"a":1,"a":2}',b'{"a":NaN}'):
   with self.assertRaises(PortabilityError):loads(b)
class Plan(unittest.TestCase):
 def test_all(self):
  p=compile_plan(inv([row('a/keep'),row('a/pub','PUBLIC_REVIEW'),row('a/cold','COLD_ARCHIVE','/srv/git/cold'),row('a/mirror','MIRROR_PRIVATE',source_url='https://github.com/a/mirror.git',destination_url='https://codeberg.org/a/mirror.git')]));self.assertEqual(p['authority'],AUTHORITY);d={x['repository']:x for x in p['repositories']};self.assertEqual(len(d['a/cold']['commands']),2);self.assertEqual(len(d['a/mirror']['commands']),4);self.assertEqual(d['a/mirror']['authority'],AUTHORITY)
 def test_bad_urls(self):
  for u in ['https://u:p@example.com/r.git','http://example.com/r.git','https://example.com/r.git?token=x','https://example.com/r.git#x','https://example.com/white space.git']:
   with self.subTest(u=u),self.assertRaises(PortabilityError):compile_plan(inv([row(action='MIRROR_PRIVATE',source_url=u,destination_url='https://codeberg.org/a/b.git')]))
 def test_paths_duplicates(self):
  for p in ['relative/r','/srv/../x']:
   with self.assertRaises(PortabilityError):compile_plan(inv([row(action='COLD_ARCHIVE',local_path=p)]))
  with self.assertRaises(PortabilityError):compile_plan(inv([row(),row()]))
 def test_contracts(self):
  bad=[row(local_path='/tmp/x'),row(action='MIRROR_PRIVATE',source_url='https://example.com/a.git'),row(action='MIRROR_PRIVATE',source_url='https://example.com/a.git',destination_url='https://example.com/a.git')]
  for r in bad:
   with self.assertRaises(PortabilityError):compile_plan(inv([r]))
 def test_exclusive_output(self):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);src=b/'i';dst=b/'o';src.write_bytes(canon(inv([row()])));p=compile_plan_file(src,dst);self.assertEqual(dst.read_bytes(),canon(p));self.assertRaises(PortabilityError,compile_plan_file,src,dst)
 def test_inventory_symlink(self):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);a=b/'a';a.write_bytes(canon(inv([row()])));l=b/'l';l.symlink_to(a);self.assertRaises(PortabilityError,compile_plan_file,l,b/'o')
 def test_pure_plan(self):
  p=compile_plan(inv([row(action='MIRROR_PRIVATE',source_url='https://nonexistent.invalid/a.git',destination_url='https://nonexistent.invalid/b.git')]));self.assertEqual(p['repositories'][0]['commands'][2]['argv'][3],'push')
 def test_cli(self):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);src=b/'i';dst=b/'o';src.write_bytes(canon(inv([row()])));opt=['-O'] if sys.flags.optimize else [];p=subprocess.run([sys.executable,*opt,str(TOOL),'plan','--inventory',str(src),'--output',str(dst)],cwd=ROOT,text=True,capture_output=True);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),json.loads(dst.read_text()))
if __name__=='__main__':unittest.main()
