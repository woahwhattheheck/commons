import json, os, pathlib, subprocess, sys, tempfile, unittest
HERE=pathlib.Path(__file__).resolve().parent; sys.path.insert(0,str(HERE)); import core
from test_train import capture
class CliTests(unittest.TestCase):
 def write_json(self,path,value): path.write_text(json.dumps(value),encoding="utf-8")
 def test_compile_markdown_verify_and_create_exclusive(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); cap=root/"capture.json"; receipt=root/"receipt.json"; md=root/"report.md"; verify=root/"verify.json"; self.write_json(cap,capture())
   cmd=[sys.executable,str(HERE/"cli.py"),"compile","--capture",str(cap),"--out",str(receipt),"--markdown",str(md)]
   first=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(first.returncode,0,first.stderr); self.assertIn("READY_FOR_GUARDED_REVIEW",md.read_text())
   second=subprocess.run(cmd,capture_output=True,text=True); self.assertEqual(second.returncode,2)
   vr=subprocess.run([sys.executable,str(HERE/"cli.py"),"verify","--receipt",str(receipt),"--capture",str(cap),"--out",str(verify)],capture_output=True,text=True); self.assertEqual(vr.returncode,0,vr.stderr); self.assertTrue(json.loads(verify.read_text())["valid"])
 @unittest.skipUnless(hasattr(os,"symlink"),"symlink unavailable")
 def test_symlink_capture_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); real=root/"real.json"; link=root/"link.json"; out=root/"out.json"; self.write_json(real,capture()); os.symlink(real,link)
   r=subprocess.run([sys.executable,str(HERE/"cli.py"),"compile","--capture",str(link),"--out",str(out)],capture_output=True,text=True); self.assertEqual(r.returncode,2); self.assertFalse(out.exists())
 def test_malformed_capture_returns_evidence_error(self):
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td); bad=root/"bad.json"; out=root/"out.json"; bad.write_text('{"a":1,"a":2}',encoding="utf-8")
   r=subprocess.run([sys.executable,str(HERE/"cli.py"),"compile","--capture",str(bad),"--out",str(out)],capture_output=True,text=True); self.assertEqual(r.returncode,2); self.assertIn("duplicate JSON key",r.stderr)
if __name__=="__main__": unittest.main(verbosity=2)
