#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
A=HERE/"acceptance.py"; M=HERE/"state_machine.json"; E=HERE/"demo_events.json"
spec=importlib.util.spec_from_file_location("onewriter_acceptance",A)
if spec is None or spec.loader is None: raise RuntimeError("could not load acceptance")
a=importlib.util.module_from_spec(spec); sys.modules[spec.name]=a; spec.loader.exec_module(a)

class OneWriterTests(unittest.TestCase):
    def setUp(self): self.m=a.load_json(M); self.d=a.load_json(E)
    def replay(self,d=None): return a.replay(copy.deepcopy(self.m),copy.deepcopy(d or self.d))
    def receipts(self): return {r["event_id"]:r for r in self.replay()["receipts"]}
    def test_baseline(self):
        s=self.replay()["summary"]; self.assertEqual((s["status"],s["event_count"],s["lane_count"]),("OK",14,3)); self.assertEqual(s["metrics"]["duplicate_touches_prevented"],4)
    def test_parallel_claim(self):
        r=self.receipts(); self.assertEqual(r["evt-001"]["decision"],"GRANTED"); self.assertEqual(r["evt-002"]["decision"],"DENIED_ACTIVE_LEASE"); self.assertEqual(r["evt-001"]["collision_key"],r["evt-002"]["collision_key"])
    def test_sent_fence_and_human_reopen(self):
        r=self.receipts(); self.assertEqual(r["evt-003"]["state"],"HARD_DNR"); self.assertEqual(r["evt-004"]["decision"],"DENIED_HARD_DNR"); self.assertEqual(r["evt-005"]["decision"],"REOPENED_HUMAN_EVENT"); self.assertEqual(r["evt-006"]["decision"],"GRANTED_AFTER_HUMAN_EVENT")
    def test_stale_recovery_and_dead_route(self):
        r=self.receipts(); self.assertEqual(r["evt-008"]["decision"],"GRANTED_STALE_RECOVERY"); self.assertEqual(r["evt-009"]["state"],"DEAD_ROUTE"); self.assertEqual(r["evt-010"]["decision"],"DENIED_DEAD_ROUTE")
    def test_hold(self):
        r=self.receipts(); self.assertEqual(r["evt-012"]["decision"],"DENIED_HOLD"); self.assertEqual(r["evt-013"]["decision"],"REOPENED_HUMAN_EVENT")
    def test_all_receipts_deny_external_authority(self): self.assertTrue(all(x["external_send_authorized"] is False for x in self.replay()["receipts"]))
    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x"; p.write_text('{"x":1,"x":2}')
            with self.assertRaisesRegex(a.ContractError,"duplicate JSON key"): a.load_json(p)
    def test_nonfinite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x"; p.write_text('{"x":NaN}')
            with self.assertRaisesRegex(a.ContractError,"non-finite"): a.load_json(p)
    def test_machine_remint(self):
        m=copy.deepcopy(self.m); m["lease"]["max_ttl_seconds"]=86400; m["contract_digest_sha256"]=hashlib.sha256(a.canonical_bytes(a.machine_semantic(m))).hexdigest()
        with self.assertRaisesRegex(a.ContractError,"lease policy changed|semantic digest"): a.validate_machine(m)
    def test_authority_escalation(self):
        m=copy.deepcopy(self.m); m["authority"]["email_send_authorized"]=True
        with self.assertRaisesRegex(a.ContractError,"all-false"): a.validate_machine(m)
    def test_duplicate_event(self):
        d=copy.deepcopy(self.d); d["events"][2]["id"]=d["events"][1]["id"]
        with self.assertRaisesRegex(a.ContractError,"duplicate event id"): a.replay(self.m,d)
    def test_reused_provider_receipt(self):
        d=copy.deepcopy(self.d); d["events"][8]["provider_receipt"]=d["events"][2]["provider_receipt"]
        with self.assertRaisesRegex(a.ContractError,"provider receipt reused"): a.replay(self.m,d)
    def test_reused_human_evidence(self):
        d=copy.deepcopy(self.d); d["events"][12]["human_evidence_id"]=d["events"][4]["human_evidence_id"]
        with self.assertRaisesRegex(a.ContractError,"human evidence reused"): a.replay(self.m,d)
    def test_nonmonotone_time(self):
        d=copy.deepcopy(self.d); d["events"][1]["at_utc"]=d["events"][0]["at_utc"]
        with self.assertRaisesRegex(a.ContractError,"strictly monotone"): a.replay(self.m,d)
    def test_nonholder_sent(self):
        d=copy.deepcopy(self.d); d["events"][2]["actor"]="agent-beta"
        with self.assertRaisesRegex(a.ContractError,"not current lease holder"): a.replay(self.m,d)
    def test_expired_holder(self):
        d=copy.deepcopy(self.d); d["events"][2]["at_utc"]="2026-09-17T12:05:01Z"
        for i,e in enumerate(d["events"][3:],start=3): e["at_utc"]=f"2026-09-17T12:{6+i:02d}:00Z"
        with self.assertRaisesRegex(a.ContractError,"lease expired"): a.replay(self.m,d)
    def test_bool_lease(self):
        d=copy.deepcopy(self.d); d["events"][0]["lease_seconds"]=True
        with self.assertRaisesRegex(a.ContractError,"bool forbidden|CLAIM lease"): a.replay(self.m,d)
    def test_extra_event_authority_field(self):
        d=copy.deepcopy(self.d); d["events"][0]["send_authorized"]=True
        with self.assertRaisesRegex(a.ContractError,"key set changed"): a.replay(self.m,d)
    def test_real_cli_normal_and_optimized(self):
        for optimized in (False,True):
            cmd=[sys.executable]+(["-O"] if optimized else [])+[str(A),"replay",str(M),str(E)]; run=subprocess.run(cmd,cwd=HERE,text=True,capture_output=True,check=False)
            with self.subTest(optimized=optimized): self.assertEqual(run.returncode,0,run.stderr); self.assertEqual(json.loads(run.stdout)["receipt_chain_sha256"],self.d["expected_summary"]["receipt_chain_sha256"])
    def test_hostile_cli_normal_and_optimized(self):
        d=copy.deepcopy(self.d); d["events"][0]["send_authorized"]=True
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"h.json"; p.write_text(json.dumps(d))
            for optimized in (False,True):
                cmd=[sys.executable]+(["-O"] if optimized else [])+[str(A),"replay",str(M),str(p)]; run=subprocess.run(cmd,cwd=HERE,text=True,capture_output=True,check=False)
                with self.subTest(optimized=optimized): self.assertEqual(run.returncode,2); self.assertIn("key set changed",run.stderr)
if __name__=="__main__": unittest.main()
