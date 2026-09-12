#!/usr/bin/env python3
from __future__ import annotations
import contextlib, io, json, tempfile, unittest
from pathlib import Path
import check_current_native_binding as gate


class V218NativeBindingTests(unittest.TestCase):
    def tree(self, *, ref=False, excluded=False, v218=False):
        td = tempfile.TemporaryDirectory(); root = Path(td.name)
        main = "from titan_runtime import TitanAgent\ndef agent(o,c=None): return TitanAgent(c).act(o)\n"
        runtime = "class TitanAgent:\n def __init__(self,c=None): pass\n def act(self,o): return {}\n"
        if ref: runtime += "\n# r04_full_router current binding\n"
        if v218: runtime += "\nV218_MOVEMENT_PARITY = True\n"
        (root/"main.py").write_text(main)
        (root/"titan_runtime.py").write_text(runtime)
        (root/"TITAN-CONFIG.json").write_text(json.dumps({"consumer":"frozen", **({"r04_v218_movement_parity":False} if v218 else {})}))
        if excluded:
            (root/"candidates").mkdir(); (root/"candidates"/"proof.py").write_text("r04_full_router v218 movement_parity")
            (root/"checks").mkdir(); (root/"checks"/"proof.json").write_text('{"v218":true}')
        return td, root

    def semantic_tree(self):
        td = tempfile.TemporaryDirectory(); root = Path(td.name)
        (root/"main.py").write_text(
            "from titan_runtime import TitanAgent, Features, load\n"
            "class FinalPressureAgent: pass\n"
            "def agent(o,c=None):\n    return FinalPressureAgent(o)\n"
        )
        (root/"titan_runtime.py").write_text(
            "from frozen_selected import FrozenSelected\n"
            "from spatial_tempo import SpatialTempo\n"
            "class TitanAgent:\n"
            "    def __init__(self):\n"
            "        self.consumer = FrozenSelected()\n"
            "        self.spatial = SpatialTempo()\n"
            "        self.controller = object()\n"
            "        self.spatial.install(self.controller)\n"
        )
        (root/"TITAN-CONFIG.json").write_text(json.dumps({"consumer":"frozen","terminal_route":False}))
        (root/"frozen_selected.py").write_text("from scheduler import *\n")
        (root/"scheduler.py").write_text(
            "parent = _load('intact_arlene', HERE/'reference/next-panel/vendor/arlene.py')\n"
        )
        arlene = root/"reference"/"next-panel"/"vendor"; arlene.mkdir(parents=True)
        (arlene/"arlene.py").write_text(
            "def _noop(op,tile,farm,private,x,y,size):\n"
            "    if op in MOVES:\n"
            "        dx,dy=MOVES[op[0]]\n"
            "        nx,ny=x+dx,y+dy\n"
            "        return not (0<=nx<size and 0<=ny<size)\n"
            "    return False\n\n"
            "def _shed_adjacent(x,y,size):\n"
            "    a=size//2-1;b=size//2\n"
            "    return (x,y) in {(a,a),(b,a),(a,b),(b,b)}\n"
        )
        (root/"spatial_tempo.py").write_text(
            "def path(a,b):\n"
            "    x,y=a;tx,ty=b;out=[]\n"
            "    while x<tx: out.append(['EAST']);x+=1\n"
            "    while x>tx: out.append(['WEST']);x-=1\n"
            "    while y<ty: out.append(['SOUTH']);y+=1\n"
            "    while y>ty: out.append(['NORTH']);y-=1\n"
            "    return out\n\n"
            "def move(pos,op,size):\n"
            "    if not op or op[0] not in MOVES:return pos\n"
            "    dx,dy=MOVES[op[0]];x,y=pos;return max(0,min(size-1,x+dx)),max(0,min(size-1,y+dy))\n"
        )
        return td, root

    def register_semantic_graph(
        self,
        root: Path,
        *,
        mutate_checker=False,
        mutate_sources=False,
        omit_source=None,
        main_drift=False,
    ):
        pkg = root/"candidates"/"v4"/"repairs"/"gameplay"/"v218-legal-movement"
        pkg.mkdir(parents=True)
        checker_rel = "repairs/gameplay/v218-legal-movement/check_current_native_binding.py"
        receipt_rel = "repairs/gameplay/v218-legal-movement/NATIVE-SEMANTIC-EQUIVALENCE.json"
        checker = b"semantic checker synthetic\n"
        (pkg/"check_current_native_binding.py").write_bytes(checker)
        source_paths = (
            "main.py",
            "titan_runtime.py",
            "frozen_selected.py",
            "scheduler.py",
            "reference/next-panel/vendor/arlene.py",
            "spatial_tempo.py",
            "TITAN-CONFIG.json",
        )
        source_ids = {rel: gate.git_blob((root/rel).read_bytes()) for rel in source_paths}
        if mutate_sources:
            source_ids["spatial_tempo.py"] = "0" * 40
        if main_drift:
            source_ids["main.py"] = "0" * 40
        if omit_source:
            source_ids.pop(omit_source, None)
        receipt = {
            "schema":"titan-v4-v218-native-semantic-equivalence/v1",
            "semantic_checker":{
                "path":checker_rel,
                "git_blob":"0"*40 if mutate_checker else gate.git_blob(checker),
            },
            "current_source_identities":source_ids,
            "control_plane_disposition":"evidence_only_no_transform_required",
            "runtime_promotion_authority":False,
            "economic_authority":False,
            "semantic_evidence":{"frozen_nonterminal_config":True},
        }
        (pkg/"NATIVE-SEMANTIC-EQUIVALENCE.json").write_text(json.dumps(receipt))
        graph = {
            "schema":"titan-v4-composition/v1",
            "components":[{
                "id":"v218-native-movement-equivalence",
                "state":"evidence_only",
                "package":"repairs/gameplay/v218-legal-movement",
                "entrypoints":[checker_rel],
                "transforms":[],
                "receipt":receipt_rel,
            }],
        }
        (root/"candidates"/"v4"/"COMPOSITION.json").write_text(json.dumps(graph))

    def test_no_ref_blocks(self):
        td,root=self.tree()
        with td:
            r=gate.audit(root)
            self.assertFalse(r["wired"]); self.assertEqual("BLOCKED_AT_NATIVE_ASSEMBLY",r["disposition"])
            self.assertEqual([],r["config"]["v218_keys"])

    def test_router_ref_wires(self):
        td,root=self.tree(ref=True)
        with td:
            r=gate.audit(root)
            self.assertTrue(r["wired"]); self.assertTrue(r["explicit_binding"]); self.assertGreater(r["router_ref_count"],0)
            self.assertEqual("WIRED_REQUIRES_RUNTIME_GATE",r["disposition"])

    def test_v218_config_is_diagnostic_not_wiring(self):
        td,root=self.tree(v218=True)
        with td:
            r=gate.audit(root)
            self.assertFalse(r["wired"]); self.assertFalse(r["explicit_binding"])
            self.assertEqual(["r04_v218_movement_parity"],r["config"]["v218_keys"])
            self.assertEqual("BLOCKED_AT_NATIVE_ASSEMBLY",r["disposition"])

    def test_excluded_evidence_not_counted(self):
        td,root=self.tree(excluded=True)
        with td:
            r=gate.audit(root)
            self.assertFalse(r["wired"]); self.assertEqual([],r["binding_refs"])

    def test_missing_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError): gate.audit(Path(td))

    def test_require_wired_exit_code(self):
        td,root=self.tree()
        with td:
            self.assertEqual(3,gate.main([str(root),"--require-wired"]))

    def test_semantic_equivalence_without_authenticated_graph_remains_blocked(self):
        td,root=self.semantic_tree()
        with td:
            r=gate.audit(root)
            self.assertFalse(r["explicit_binding"])
            self.assertTrue(r["native_semantic_equivalence"]["equivalent"])
            self.assertFalse(r["semantic_wired"])
            self.assertFalse(r["wired"])
            self.assertEqual("missing_canonical_composition_graph",r["semantic_graph_registration"]["reason"])
            self.assertEqual("BLOCKED_AT_GRAPH_REGISTRATION",r["disposition"])

    def test_authenticated_graph_receipt_wires_semantic_equivalence(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root)
            r=gate.audit(root)
            self.assertTrue(r["native_semantic_equivalence"]["equivalent"])
            self.assertTrue(r["semantic_wired"])
            self.assertTrue(r["wired"])
            self.assertEqual("authenticated_evidence_only_semantic_edge",r["semantic_graph_registration"]["reason"])
            self.assertEqual(
                {
                    "main.py",
                    "titan_runtime.py",
                    "frozen_selected.py",
                    "scheduler.py",
                    "reference/next-panel/vendor/arlene.py",
                    "spatial_tempo.py",
                    "TITAN-CONFIG.json",
                },
                set(r["semantic_graph_registration"]["source_identities"]),
            )
            self.assertEqual("NATIVE_SEMANTIC_EQUIVALENT_REQUIRES_RUNTIME_GATE",r["disposition"])

    def test_semantic_graph_receipt_checker_drift_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root,mutate_checker=True)
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"]); self.assertFalse(r["wired"])
            self.assertEqual("checker_identity_mismatch",r["semantic_graph_registration"]["reason"])

    def test_semantic_graph_receipt_source_drift_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root,mutate_sources=True)
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"]); self.assertFalse(r["wired"])
            self.assertEqual("semantic_source_identity_mismatch",r["semantic_graph_registration"]["reason"])

    def test_semantic_graph_receipt_main_drift_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root,main_drift=True)
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"]); self.assertFalse(r["wired"])
            self.assertEqual("semantic_source_identity_mismatch",r["semantic_graph_registration"]["reason"])

    def test_semantic_graph_receipt_source_omission_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root,omit_source="scheduler.py")
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"]); self.assertFalse(r["wired"])
            self.assertEqual("semantic_source_identity_set_mismatch",r["semantic_graph_registration"]["reason"])
            self.assertIn("scheduler.py",r["semantic_graph_registration"]["expected_paths"])

    def test_semantic_graph_duplicate_component_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root)
            graph_path=root/"candidates"/"v4"/"COMPOSITION.json"
            graph=json.loads(graph_path.read_text()); graph["components"].append(dict(graph["components"][0]))
            graph_path.write_text(json.dumps(graph))
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"])
            self.assertEqual("semantic_component_cardinality",r["semantic_graph_registration"]["reason"])

    def test_semantic_graph_duplicate_json_key_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root)
            graph_path=root/"candidates"/"v4"/"COMPOSITION.json"
            graph_path.write_text('{"schema":"titan-v4-composition/v1","schema":"titan-v4-composition/v1","components":[]}')
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"])
            self.assertEqual("invalid_canonical_composition_graph",r["semantic_graph_registration"]["reason"])

    def test_semantic_graph_nonfinite_json_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root)
            graph_path=root/"candidates"/"v4"/"COMPOSITION.json"
            graph_path.write_text('{"schema":"titan-v4-composition/v1","components":[],"bad":NaN}')
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"])
            self.assertEqual("invalid_canonical_composition_graph",r["semantic_graph_registration"]["reason"])

    def test_semantic_receipt_duplicate_json_key_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root)
            receipt_path=root/"candidates"/"v4"/"repairs"/"gameplay"/"v218-legal-movement"/"NATIVE-SEMANTIC-EQUIVALENCE.json"
            receipt_path.write_text('{"schema":"titan-v4-v218-native-semantic-equivalence/v1","schema":"titan-v4-v218-native-semantic-equivalence/v1"}')
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"])
            self.assertEqual("invalid_semantic_receipt",r["semantic_graph_registration"]["reason"])

    def test_semantic_receipt_nonfinite_json_is_rejected(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root)
            receipt_path=root/"candidates"/"v4"/"repairs"/"gameplay"/"v218-legal-movement"/"NATIVE-SEMANTIC-EQUIVALENCE.json"
            receipt_path.write_text('{"schema":"titan-v4-v218-native-semantic-equivalence/v1","bad":Infinity}')
            r=gate.audit(root)
            self.assertFalse(r["semantic_wired"])
            self.assertEqual("invalid_semantic_receipt",r["semantic_graph_registration"]["reason"])

    def test_cli_success_for_authenticated_semantic_equivalence(self):
        td,root=self.semantic_tree()
        with td:
            self.register_semantic_graph(root)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0,gate.main([str(root),"--require-wired"]))


if __name__ == "__main__": unittest.main()
