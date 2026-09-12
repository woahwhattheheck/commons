import json, tempfile, unittest
from pathlib import Path
import check_current_native_binding as g


class TestGate(unittest.TestCase):
    def tree(self, td, main='def agent(o,c=None): return {}\n',
             runtime='class X: pass\n', cfg=None, extra=None):
        r=Path(td)
        (r/'main.py').write_text(main)
        (r/'titan_runtime.py').write_text(runtime)
        (r/'TITAN-CONFIG.json').write_text(
            json.dumps({"consumer":"frozen"} if cfg is None else cfg)
        )
        if extra:
            for name,text in extra.items():
                p=r/name
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(text)
        return r

    def semantic_tree(self, td, *, locked_bug=False, shed_bug=False):
        move_body = (
            "  if tile == 'LOCKED': return True\n"
            if locked_bug else ""
        )
        shed = (
            " return (x,y) in ((h-1,h-1),(h,h-1),(h-1,h))\n"
            if shed_bug else
            " return (x,y) in ((h-1,h-1),(h,h-1),(h-1,h),(h,h))\n"
        )
        arlene = (
            "BOARD=10\n"
            "MOVES={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0),'WEST':(-1,0)}\n"
            "ANIMALS={}\n"
            "def _shed_adjacent(x,y,board=BOARD):\n"
            " h=board//2\n" + shed +
            "def _noop(act,tile,inv,seeds,x,y,board=BOARD):\n"
            " if not act:return True\n"
            " op=act[0]\n"
            " if op in MOVES:\n" +
            move_body +
            "  dx,dy=MOVES[op]\n"
            "  return not (0<=x+dx<board and 0<=y+dy<board)\n"
            " if op=='PASS':return True\n"
            " if tile=='LOCKED':return True\n"
            " return False\n"
        )
        spatial = (
            "MOVES={'NORTH':(0,-1),'SOUTH':(0,1),'EAST':(1,0),'WEST':(-1,0)}\n"
            "def move(pos,action,board):\n"
            " d=MOVES.get(action[0] if action else '')\n"
            " if d:\n"
            "  q=(pos[0]+d[0],pos[1]+d[1])\n"
            "  if 0<=q[0]<board and 0<=q[1]<board:return q\n"
            " return pos\n"
            "def path(a,b):\n"
            " return [[('EAST' if b[0]>a[0] else 'WEST')]]*abs(b[0]-a[0])+[[('SOUTH' if b[1]>a[1] else 'NORTH')]]*abs(b[1]-a[1])\n"
        )
        return self.tree(
            td,
            main=(
                "from titan_runtime import TitanAgent, Features, load\n"
                "def f(features):\n"
                " return FinalPressureAgent(features)\n"
            ),
            runtime=(
                "from frozen_selected import FrozenSelected\n"
                "from spatial_tempo import SpatialTempo\n"
                "class X:\n"
                " def f(self):\n"
                "  self.consumer = FrozenSelected()\n"
                "  self.spatial.install(self.controller)\n"
            ),
            cfg={"consumer":"frozen","terminal_route":False},
            extra={
                "frozen_selected.py":"from scheduler import *\n",
                "scheduler.py":"parent = _load('intact_arlene', HERE/'reference/next-panel/vendor/arlene.py')\n",
                "reference/next-panel/vendor/arlene.py":arlene,
                "spatial_tempo.py":spatial,
            },
        )

    def test_unwired_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td))
            self.assertFalse(x['wired'])
            self.assertEqual(x['disposition'],'BLOCKED_AT_NATIVE_ASSEMBLY')

    def test_router_reference_wires(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td, runtime='from r04_full_router import install\n'))
            self.assertTrue(x['wired'])
            self.assertTrue(x['explicit_binding'])
            self.assertEqual(x['disposition'],'WIRED_REQUIRES_RUNTIME_GATE')

    def test_v218_config_wires(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td,cfg={'r04_v218_movement_parity':False}))
            self.assertTrue(x['wired'])
            self.assertEqual(x['config']['v218_keys'],['r04_v218_movement_parity'])

    def test_reference_checks_do_not_fake_wiring(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.tree(td,extra={'checks/reference/note.py':'r04_full_router v218'}))
            self.assertFalse(x['wired'])

    def test_native_semantic_equivalence_wires_without_v218_token(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.semantic_tree(td))
            self.assertFalse(x['explicit_binding'])
            self.assertTrue(x['native_semantic_equivalence']['equivalent'])
            self.assertTrue(x['wired'])
            self.assertEqual(
                x['disposition'],
                'NATIVE_SEMANTIC_EQUIVALENT_REQUIRES_RUNTIME_GATE',
            )
            self.assertTrue(all(x['native_semantic_equivalence']['rules'].values()))
            self.assertTrue(all(x['native_semantic_equivalence']['call_chain'].values()))

    def test_locked_move_bug_fails_equivalence(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.semantic_tree(td, locked_bug=True))
            self.assertFalse(x['native_semantic_equivalence']['equivalent'])
            self.assertFalse(x['native_semantic_equivalence']['rules']['locked_transit_matches_engine'])
            self.assertFalse(x['wired'])

    def test_three_corner_shed_bug_fails_equivalence(self):
        with tempfile.TemporaryDirectory() as td:
            x=g.audit(self.semantic_tree(td, shed_bug=True))
            self.assertFalse(x['native_semantic_equivalence']['equivalent'])
            self.assertFalse(x['native_semantic_equivalence']['rules']['all_four_shed_corners_eligible'])
            self.assertFalse(x['wired'])

    def test_missing_required_fails(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            (r/'main.py').write_text('')
            (r/'TITAN-CONFIG.json').write_text('{}')
            with self.assertRaises(ValueError):
                g.audit(r)

    def test_cli_require_wired_exit3(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.tree(td)
            self.assertEqual(g.main([str(r),'--require-wired']),3)

    def test_cli_semantic_equivalence_satisfies_require_wired(self):
        with tempfile.TemporaryDirectory() as td:
            r=self.semantic_tree(td)
            self.assertEqual(g.main([str(r),'--require-wired']),0)


if __name__=='__main__':
    unittest.main()
