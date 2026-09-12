import json, tempfile, unittest
from pathlib import Path
import check_current_native_binding as g

class TestGate(unittest.TestCase):
    def tree(self, td, main='def agent(o,c=None): return {}\n', runtime='class X: pass\n', cfg=None, extra=None):
        r=Path(td); (r/'main.py').write_text(main); (r/'titan_runtime.py').write_text(runtime)
        (r/'TITAN-CONFIG.json').write_text(json.dumps({"consumer":"frozen"} if cfg is None else cfg))
        if extra:
            for name,text in extra.items():
                p=r/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
        return r
    def test_unwired_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td)); self.assertFalse(x['wired']); self.assertEqual(x['disposition'],'BLOCKED_AT_NATIVE_ASSEMBLY')
    def test_router_reference_wires(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td, runtime='from r04_full_router import install\n')); self.assertTrue(x['wired'])
    def test_v218_config_wires(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td,cfg={'r04_v218_movement_parity':False})); self.assertTrue(x['wired']); self.assertEqual(x['config']['v218_keys'],['r04_v218_movement_parity'])
    def test_reference_checks_do_not_fake_wiring(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td,extra={'checks/reference/note.py':'r04_full_router v218'})); self.assertFalse(x['wired'])
    def test_missing_required_fails(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/'main.py').write_text(''); (r/'TITAN-CONFIG.json').write_text('{}')
            with self.assertRaises(ValueError): g.audit(r)
    def test_cli_require_wired_exit3(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.tree(td); self.assertEqual(g.main([str(r),'--require-wired']),3)

if __name__=='__main__': unittest.main()
