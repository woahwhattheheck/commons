import importlib.util, json, tempfile, unittest
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def mod(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file); m=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(m); return m
compiler=mod("compiler","compiler.py"); synthetic=mod("synthetic","synthetic_acceptance.py")

class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.jobs,cls.plan=synthetic.build_corpus(); cls.result=compiler.compile_run(cls.jobs)
    def test_frozen_shape(self):
        self.assertEqual(120,len(self.jobs)); ids=[x for xs in self.plan.values() for x in xs]; self.assertEqual(24,len(ids)); self.assertEqual(24,len(set(ids))); self.assertTrue(all(len(v)==3 for v in self.plan.values()))
    def test_exact_96_24(self):
        s=self.result["summary"]; self.assertEqual(96,s["complete_packets"]); self.assertEqual(24,s["exceptions"]); self.assertEqual(24,s["unique_exception_jobs"]); self.assertEqual(0,s["control_commands_emitted"])
    def test_exact_three_per_eight_classes(self):
        c=Counter(e["input_class"] for e in self.result["exceptions"]); self.assertEqual({k:3 for k in synthetic.FAULT_CLASSES},dict(c)); self.assertEqual(8,len(c))
    def test_one_reason_per_faulty_job(self):
        c=Counter(e["job_ref"] for e in self.result["exceptions"]); self.assertEqual(24,len(c)); self.assertTrue(all(v==1 for v in c.values()))
    def test_lineage_is_exact_source_copy(self):
        src={j["job_id"]:j for j in self.jobs if j["job_id"]}
        for p in self.result["packets"]:
            for path,item in p["lineage"].items(): self.assertEqual(path,item["source"]); self.assertEqual(compiler.resolve_path(src[p["job_id"]],path),item["value"])
    def test_zero_control_or_release(self):
        for p in self.result["packets"]: self.assertEqual(0,p["control_commands_emitted"]); self.assertIsNone(p["field_release"]); self.assertIn("no robot motion/printing",p["boundary"])
        for e in self.result["exceptions"]: self.assertEqual(0,e["control_commands_emitted"]); self.assertIsNone(e["field_release"])
    def test_deterministic_bundle(self):
        repeat=compiler.compile_run(self.jobs); self.assertEqual(json.dumps(self.result,sort_keys=True),json.dumps(repeat,sort_keys=True))
        with tempfile.TemporaryDirectory() as t:
            out=Path(t); compiler.write_bundle(self.result,out); self.assertEqual(96,len(list((out/"packets").glob("*.json")))); self.assertEqual(24,len((out/"exceptions.jsonl").read_text().splitlines()))

if __name__=="__main__": unittest.main()
