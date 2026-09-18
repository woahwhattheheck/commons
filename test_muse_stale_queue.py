from __future__ import annotations
import copy, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from coordination import muse_stale_queue as m

class T(unittest.TestCase):
    def event(self,kind,sec=0,op="OP-1",eid=None,receipt=None,**kw):
        actor={"REQUEST":"REQUESTER","SELECTED":"MUSE","HOLD":"MUSE","COLLISION":"MUSE","LEASED":"RUNTIME","CONSUMED":"RUNTIME","GO":"RUNTIME","PROVIDER_SENT":"PROVIDER","PROVIDER_CONSUMED":"PROVIDER","PROVIDER_DNR":"PROVIDER","WITHDRAW":"OPERATOR","RELEASE":"RUNTIME","SUPERSEDE":"OPERATOR"}[kind]
        x={"event_id":eid or f"e-{op}-{kind}-{sec}","operation_key":op,"actor_class":actor,"event_kind":kind,"occurred_at":f"2026-09-17T23:{sec//60:02d}:{sec%60:02d}Z","source_ref":f"slack:{op}:{sec}","counterparty":"Acme","route":"sales@example.test","purpose":"paid workshare","seat":"Z-1","provider_receipt_id":receipt}
        x.update(kw); return x
    def packet(self,events,eval="2026-09-17T23:10:00Z",cap="2026-09-17T23:10:00Z",stale=120,ttl=180,maxage=30):
        return {"schema":m.PACKET_SCHEMA,"captured_at":cap,"evaluated_at":eval,"stale_after_seconds":stale,"selection_ttl_seconds":ttl,"max_capture_age_seconds":maxage,"events":events}
    def comp(self,p): return m.compile_packet(json.dumps(p,separators=(",",":")).encode())
    def state(self,p): return self.comp(p)[0]["operations"][0]
    def req(self,sec=0,**kw): return self.event("REQUEST",sec,**kw)
    def test_unanswered_stale_and_authority_false(self):
        r,md=self.comp(self.packet([self.req()])); o=r["operations"][0]
        self.assertEqual(o["state"],"UNANSWERED_STALE"); self.assertTrue(o["requires_fresh_arbitration"]); self.assertIn("OP-1",md); self.assertTrue(all(v is False for v in r["authority"].values()))
    def test_fresh_boundary(self):
        p=self.packet([self.req(0)],eval="2026-09-17T23:02:00Z",cap="2026-09-17T23:02:00Z"); self.assertEqual(self.state(p)["state"],"FRESH_PENDING")
    def test_bare_selected_expiry_requires_fresh(self):
        p=self.packet([self.req(),self.event("SELECTED",10)],ttl=180); o=self.state(p); self.assertEqual(o["state"],"BARE_SELECTED_STALE"); self.assertTrue(o["requires_fresh_arbitration"])
    def test_selected_inside_ttl_pending(self):
        p=self.packet([self.req(),self.event("SELECTED",10)],eval="2026-09-17T23:02:00Z",cap="2026-09-17T23:02:00Z"); self.assertEqual(self.state(p)["state"],"FRESH_PENDING")
    def test_atomic_sequence_pending_provider_never_resurface(self):
        es=[self.req(),self.event("SELECTED",10),self.event("LEASED",20),self.event("CONSUMED",30),self.event("GO",40)]; o=self.state(self.packet(es)); self.assertEqual(o["state"],"CONSUMED_PENDING_PROVIDER"); self.assertFalse(o["resurface_recommended"])
    def test_provider_terminals_close(self):
        for k in ("PROVIDER_SENT","PROVIDER_CONSUMED","PROVIDER_DNR"):
            with self.subTest(k=k):
                es=[self.req(),self.event("SELECTED",10),self.event("LEASED",20),self.event("CONSUMED",30),self.event("GO",40),self.event(k,50,receipt="r-1")]; self.assertEqual(self.state(self.packet(es))["state"],"TERMINAL_SENT")
    def test_release_terminals_close(self):
        for k in ("WITHDRAW","RELEASE","SUPERSEDE"):
            with self.subTest(k=k): self.assertEqual(self.state(self.packet([self.req(),self.event(k,20)]))["state"],"TERMINAL_RELEASED")
    def test_hold_collision(self):
        for k in ("HOLD","COLLISION"):
            with self.subTest(k=k): self.assertEqual(self.state(self.packet([self.req(),self.event(k,20)]))["state"],"HOLD_OR_COLLISION")
    def test_identity_drift_and_chronology_fail_closed(self):
        es=[self.req(),self.event("SELECTED",10,route="other@example.test")]; self.assertEqual(self.state(self.packet(es))["state"],"HOLD_EVIDENCE")
        es=[self.req(20),self.event("SELECTED",10)]; self.assertEqual(self.state(self.packet(es))["state"],"HOLD_EVIDENCE")
    def test_atomic_missing_steps_fail_closed(self):
        cases=[[self.req(),self.event("CONSUMED",10)],[self.req(),self.event("GO",10)],[self.req(),self.event("SELECTED",10),self.event("PROVIDER_SENT",20,receipt="r")]]
        for es in cases:
            with self.subTest(es=[x["event_kind"] for x in es]): self.assertEqual(self.state(self.packet(es))["state"],"HOLD_EVIDENCE")
    def test_duplicate_event_and_request_fail_closed(self):
        es=[self.req(eid="same"),self.event("SELECTED",10,eid="same")]; self.assertEqual(self.state(self.packet(es))["state"],"HOLD_EVIDENCE")
        es=[self.req(),self.req(10,eid="r2")]; self.assertEqual(self.state(self.packet(es))["state"],"HOLD_EVIDENCE")
    def test_provider_receipt_cross_key_reuse_fails_both(self):
        es=[]
        for op in ("OP-1","OP-2"):
            es += [self.req(op=op,eid=f"{op}-r"),self.event("SELECTED",10,op=op,eid=f"{op}-s"),self.event("LEASED",20,op=op,eid=f"{op}-l"),self.event("CONSUMED",30,op=op,eid=f"{op}-c"),self.event("GO",40,op=op,eid=f"{op}-g"),self.event("PROVIDER_SENT",50,op=op,eid=f"{op}-p",receipt="same-r")]
        r,_=self.comp(self.packet(es)); self.assertEqual({x["state"] for x in r["operations"]},{"HOLD_EVIDENCE"})
    def test_future_after_capture_and_stale_capture_fail_closed(self):
        p=self.packet([self.req(),self.event("SELECTED",11*60)],eval="2026-09-17T23:10:00Z",cap="2026-09-17T23:10:00Z"); self.assertEqual(self.state(p)["state"],"HOLD_EVIDENCE")
        p=self.packet([self.req()],eval="2026-09-17T23:10:31Z",cap="2026-09-17T23:10:00Z",maxage=30); self.assertEqual(self.state(p)["state"],"HOLD_EVIDENCE")
    def test_duplicate_json_float_bool_unsafe_int_unknown_field_rejected(self):
        base=json.dumps(self.packet([self.req()]),separators=(",",":"))
        bad=[base.replace('"schema":','"schema":"x","schema":',1),base.replace('"stale_after_seconds":120','"stale_after_seconds":1.5'),base.replace('"stale_after_seconds":120','"stale_after_seconds":true'),base.replace('"stale_after_seconds":120','"stale_after_seconds":9007199254740992'),base[:-1]+',"extra":1}']
        for raw in bad:
            with self.subTest(raw=raw[-40:]): self.assertRaises(m.Error,m.compile_packet,raw.encode())
    def test_unsafe_text_and_actor_kind_rejected(self):
        p=self.packet([self.req(route="bad\nroute")]); self.assertRaises(m.Error,self.comp,p)
        p=self.packet([self.req()]); p["events"][0]["actor_class"]="MUSE"; self.assertRaises(m.Error,self.comp,p)
    def test_deterministic_event_input_order_semantics(self):
        es=[self.req(),self.event("SELECTED",10),self.event("LEASED",20),self.event("CONSUMED",30),self.event("GO",40)]; a,_=self.comp(self.packet(es)); b,_=self.comp(self.packet(list(reversed(es))));
        for r in (a,b): r.pop("packet_sha256"); r.pop("semantic_receipt_sha256")
        self.assertEqual(a,b)
    def test_authority_template_mutation_and_rebinding_cannot_widen(self):
        raw=json.dumps(self.packet([self.req()]),separators=(",",":")).encode(); saved=copy.deepcopy(m.AUTH)
        try:
            m.AUTH["external_send_authorized"]=True
            a,amd=m.compile_packet(raw); self.assertTrue(all(v is False for v in a["authority"].values())); self.assertTrue(m.verify_compiled(raw,a,amd))
            m.AUTH={"external_send_authorized":True,"muse_selection_authorized":True,"provider_action_authorized":True,"payment_authorized":True,"cash_proven":True,"revenue_recognized":True}
            b,bmd=m.compile_packet(raw); self.assertTrue(all(v is False for v in b["authority"].values())); self.assertTrue(m.verify_compiled(raw,b,bmd))
        finally: m.AUTH=saved
    def test_release_family_is_terminal(self):
        for term in ("WITHDRAW","RELEASE","SUPERSEDE"):
            with self.subTest(term=term,later="SELECTED"):
                es=[self.req(),self.event(term,10),self.event("SELECTED",20)]
                self.assertEqual(self.state(self.packet(es))["state"],"HOLD_EVIDENCE")
            with self.subTest(term=term,later="ATOMIC"):
                es=[self.req(),self.event("SELECTED",5),self.event(term,10),self.event("LEASED",20),self.event("CONSUMED",30),self.event("GO",40)]
                self.assertEqual(self.state(self.packet(es))["state"],"HOLD_EVIDENCE")
    def test_verify_detects_report_markdown_tamper(self):
        raw=json.dumps(self.packet([self.req()]),separators=(",",":")).encode(); r,md=m.compile_packet(raw); self.assertTrue(m.verify_compiled(raw,r,md)); q=copy.deepcopy(r); q["authority"]["cash_proven"]=True; self.assertFalse(m.verify_compiled(raw,q,md)); self.assertFalse(m.verify_compiled(raw,r,md+"x"))
    def test_markdown_escapes_table_html(self):
        p=self.packet([self.req(route="x|<script>@example.test")]); _,md=self.comp(p); self.assertNotIn("<script>",md); self.assertIn("\\|",md); self.assertIn("&lt;script&gt;",md)
    def test_cli_compile_verify_create_only(self):
        raw=json.dumps(self.packet([self.req()]),separators=(",",":")).encode()
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); (d/"p.json").write_bytes(raw); env=dict(os.environ); env["PYTHONPATH"]=str(Path(__file__).parent)+os.pathsep+env.get("PYTHONPATH","")
            cmd=[sys.executable,"-m","coordination.muse_stale_queue"]
            a=subprocess.run(cmd+["compile",str(d/"p.json"),str(d/"r.json"),str(d/"q.md")],env=env,capture_output=True,text=True); self.assertEqual(a.returncode,0,a.stderr)
            b=subprocess.run(cmd+["verify",str(d/"p.json"),str(d/"r.json"),str(d/"q.md")],env=env,capture_output=True,text=True); self.assertEqual(b.returncode,0,b.stderr); self.assertIn("VALID",b.stdout)
            c=subprocess.run(cmd+["compile",str(d/"p.json"),str(d/"r.json"),str(d/"q2.md")],env=env,capture_output=True,text=True); self.assertEqual(c.returncode,2)
if __name__=="__main__": unittest.main()
