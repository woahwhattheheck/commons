from __future__ import annotations
from datetime import datetime, timezone
import json, os
from pathlib import Path
import subprocess, sys, tempfile, unittest
from tools.provider_cost_truth import codec, engine, evaluator, gate, schema
from tools.provider_cost_truth._test_support import NOW,event,snapshot

ROOT=Path(__file__).resolve().parents[2]

class ProviderCostTruthHostiles(unittest.TestCase):
    def test_explicit_time_evaluator_cannot_mint_current_receipt(self):
        r=engine._evaluate_snapshot(snapshot([event("a-zero")]),NOW)
        for forbidden in("evaluation_mode","evaluated_at_utc","receipt_sha256"):self.assertNotIn(forbidden,r)
        self.assertFalse(hasattr(gate,"_compile_at"));self.assertFalse(hasattr(engine,"_construct_api"));self.assertFalse(hasattr(engine,"_seal"))

    def test_ordinary_module_rebinding_cannot_retarget_supported_current_api(self):
        snap=snapshot([event("a-zero")])
        originals=(engine._DateTime,engine._evaluate_snapshot,evaluator._billing_class,schema.validate_snapshot,codec._canonical_bytes)
        class FakeDateTime:
            @classmethod
            def now(cls,tz=None):return datetime(2001,1,1,tzinfo=timezone.utc)
        def bomb(*args,**kwargs):raise AssertionError("rebound module helper was consulted")
        try:
            engine._DateTime=FakeDateTime;engine._evaluate_snapshot=bomb;evaluator._billing_class=bomb;schema.validate_snapshot=bomb;codec._canonical_bytes=bomb
            r=engine.compile_current(snap);self.assertEqual(r["state"],"ZERO_COST_VERIFIED");self.assertGreaterEqual(r["evaluated_at_utc"],"2026-09-17T00:00:00Z");self.assertTrue(engine.verify_receipt(snap,r))
        finally:
            engine._DateTime,engine._evaluate_snapshot,evaluator._billing_class,schema.validate_snapshot,codec._canonical_bytes=originals

    def test_lone_surrogate_value_rejected_as_gate_error(self):
        bad=snapshot([]);bad["request"]["provider"]="\ud800"
        with self.assertRaisesRegex(gate.GateError,"invalid Unicode scalar"):engine._evaluate_snapshot(bad,NOW)

    def test_escaped_surrogate_object_key_is_ascii_safe_gate_error(self):
        with self.assertRaises(gate.GateError) as ctx:gate.loads_strict_json('{"\\ud800":1,"\\ud800":2}')
        str(ctx.exception).encode("ascii","strict")

    def test_receipt_surrogate_reason_is_rejected_before_canonicalization(self):
        snap=snapshot([event("a-zero")]);r=gate.compile_current(snap);r["reasons"]=["\ud800"]
        with self.assertRaisesRegex(gate.GateError,"invalid Unicode scalar"):gate.verify_receipt(snap,r)

    def test_cli_surrogate_input_is_rc2_normal_and_optimized(self):
        bad=snapshot([]);bad["request"]["provider"]="\ud800"
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"surrogate.json";path.write_text(json.dumps(bad),encoding="utf-8");env=dict(os.environ);env["PYTHONIOENCODING"]="utf-8:strict"
            for command in([sys.executable],[sys.executable,"-O"]):
                result=subprocess.run(command+["-m","tools.provider_cost_truth.cli","compile",str(path)],cwd=ROOT,text=True,capture_output=True,env=env,check=False);combined=result.stdout+result.stderr
                self.assertEqual(result.returncode,2,combined);self.assertIn("ERROR:",result.stderr);self.assertNotIn("Traceback",combined);self.assertNotIn("UnicodeEncodeError",combined)

if __name__=="__main__":unittest.main()
