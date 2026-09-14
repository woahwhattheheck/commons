import ast, subprocess, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'submission_src'))
class PublicContractTests(unittest.TestCase):
    def test_all_python_compiles(self):
        for p in ROOT.rglob('*.py'): ast.parse(p.read_text(), filename=str(p))
    def test_public_tree_guard(self):
        r=subprocess.run([sys.executable,str(ROOT/'scripts/verify_public_tree.py'),str(ROOT)],capture_output=True,text=True); self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertIn('PASS',r.stdout)
    def test_main_has_official_paths_and_no_network(self):
        text=(ROOT/'submission_src/main.py').read_text(); self.assertIn('/code_execution/data',text); self.assertIn('submission_format.csv',text); self.assertIn('is_pathologic',text)
        for token in ('requests','urllib','socket','http://','https://'): self.assertNotIn(token,text)
    def test_inference_has_single_scan_api(self):
        tree=ast.parse((ROOT/'submission_src/datpark/inference.py').read_text()); names={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}; self.assertIn('predict_one',names)
    def test_no_challenge_artifacts_exist(self):
        names={p.name for p in ROOT.rglob('*') if p.is_file()}; self.assertFalse({'train_labels.csv','submission.csv','submission.zip'} & names)
if __name__=='__main__': unittest.main()
