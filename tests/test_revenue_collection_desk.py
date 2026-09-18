from __future__ import annotations
import copy, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from tools.revenue_collection_desk.core import CollectionError, artifact_bundle, compile_ledger, load_json_bytes, verify_ledger

BASE={
 'schema':'revenue-collection-desk/source/v1','as_of':'2026-09-18T12:00:00Z','claims':[{
  'claim_id':'C1','counterparty_id':'CP1','work_ref':'W1','instrument':'USD','amount':'1250.00','reference_value_usd':None,
  'events':[
   {'event_id':'E1','at':'2026-09-16T12:00:00Z','kind':'WORK_SUBMITTED','source_ref':'S1','data':{'amount':'1250.00','instrument':'USD'}},
   {'event_id':'E2','at':'2026-09-17T12:00:00Z','kind':'ACCEPTED_AWAITING_PAYMENT','source_ref':'S2','data':{'amount':'1250.00','instrument':'USD'}},
  ]
 }]}

def ev(eid,at,kind,data,src=None): return {'event_id':eid,'at':at,'kind':kind,'source_ref':src or eid+'SRC','data':data}

def add(src,*events):
 x=copy.deepcopy(src); x['claims'][0]['events']+=list(events); return x

class DeskTests(unittest.TestCase):
 def test_acceptance_is_not_cash(self):
  r=compile_ledger(BASE); self.assertEqual(r['payload']['totals_by_instrument']['USD']['accepted_outstanding'],'1250'); self.assertEqual(r['payload']['totals_by_instrument']['USD']['settled_cash'],'0')
 def test_asserted_hold_waits(self):
  s=add(BASE,ev('E3','2026-09-18T08:00:00Z','PAYMENT_ASSERTED_HOLD',{'amount':'1250.00','instrument':'USD','hold_until':'2026-09-20T00:00:00Z'})); r=compile_ledger(s); self.assertEqual(r['payload']['claims'][0]['next_action'],'WAIT_HOLD'); self.assertEqual(r['payload']['totals_by_instrument']['USD']['settled_cash'],'0')
 def test_expired_hold_verifies_available(self):
  s=add(BASE,ev('E3','2026-09-17T13:00:00Z','PAYMENT_ASSERTED_HOLD',{'amount':'1250.00','instrument':'USD','hold_until':'2026-09-18T10:00:00Z'})); self.assertEqual(compile_ledger(s)['payload']['claims'][0]['next_action'],'VERIFY_AVAILABLE')
 def test_available_is_not_settled(self):
  s=add(BASE,ev('E3','2026-09-18T08:00:00Z','PAYMENT_AVAILABLE',{'amount':'1250.00','instrument':'USD'})); r=compile_ledger(s); self.assertEqual(r['payload']['claims'][0]['next_action'],'VERIFY_SETTLEMENT'); self.assertEqual(r['payload']['totals_by_instrument']['USD']['available_not_settled'],'1250'); self.assertEqual(r['payload']['totals_by_instrument']['USD']['settled_cash'],'0')
 def test_settlement_is_cash(self):
  s=add(BASE,ev('E3','2026-09-18T07:00:00Z','PAYMENT_AVAILABLE',{'amount':'1250.00','instrument':'USD'}),ev('E4','2026-09-18T08:00:00Z','SETTLED_CASH',{'amount':'1250.00','instrument':'USD','settlement_ref':'BANK-1'})); r=compile_ledger(s); self.assertEqual(r['payload']['claims'][0]['next_action'],'DONE'); self.assertEqual(r['payload']['totals_by_instrument']['USD']['settled_cash'],'1250')
 def test_reference_value_never_becomes_usd(self):
  s=copy.deepcopy(BASE); c=s['claims'][0]; c['instrument']='RTC'; c['amount']='500'; c['reference_value_usd']='75.00'
  for e in c['events']: e['data']={'amount':'500','instrument':'RTC'}
  r=compile_ledger(s); self.assertIn('RTC',r['payload']['totals_by_instrument']); self.assertNotIn('USD',r['payload']['totals_by_instrument'])
 def test_release_required_for_collection(self):
  self.assertEqual(compile_ledger(BASE)['payload']['claims'][0]['next_action'],'WAIT_REPLY')
  s=add(BASE,ev('E3','2026-09-18T08:00:00Z','COLLECTION_RELEASED',{'not_before':'2026-09-18T09:00:00Z','expires_at':'2026-09-19T09:00:00Z'})); self.assertEqual(compile_ledger(s)['payload']['claims'][0]['next_action'],'COLLECTION_ELIGIBLE')
 def test_silence_never_reauthorizes_retry(self):
  s=add(BASE,ev('E3','2026-09-18T07:00:00Z','COLLECTION_RELEASED',{'not_before':'2026-09-18T07:00:00Z','expires_at':'2026-09-20T00:00:00Z'}),ev('E4','2026-09-18T08:00:00Z','COLLECTION_CONTACT',{'delivery':'DELIVERED','dnr_until':None})); self.assertEqual(compile_ledger(s)['payload']['claims'][0]['next_action'],'WAIT_REPLY')
 def test_fresh_release_can_reauthorize(self):
  s=add(BASE,ev('E3','2026-09-18T07:00:00Z','COLLECTION_CONTACT',{'delivery':'DELIVERED','dnr_until':None}),ev('E4','2026-09-18T08:00:00Z','COLLECTION_RELEASED',{'not_before':'2026-09-18T08:00:00Z','expires_at':'2026-09-19T08:00:00Z'})); self.assertEqual(compile_ledger(s)['payload']['claims'][0]['next_action'],'COLLECTION_ELIGIBLE')
 def test_dnr_blocks_fresh_release(self):
  s=add(BASE,ev('E3','2026-09-18T07:00:00Z','COLLECTION_CONTACT',{'delivery':'DELIVERED','dnr_until':'2026-09-20T00:00:00Z'}),ev('E4','2026-09-18T08:00:00Z','COLLECTION_RELEASED',{'not_before':'2026-09-18T08:00:00Z','expires_at':'2026-09-19T08:00:00Z'})); self.assertEqual(compile_ledger(s)['payload']['claims'][0]['next_action'],'WAIT_REPLY')
 def test_bounce_requires_route_repair(self):
  s=add(BASE,ev('E3','2026-09-18T08:00:00Z','COLLECTION_CONTACT',{'delivery':'BOUNCED','dnr_until':None})); self.assertEqual(compile_ledger(s)['payload']['claims'][0]['next_action'],'ROUTE_REPAIR_REQUIRED')
 def test_repair_does_not_authorize_send(self):
  s=add(BASE,ev('E3','2026-09-18T07:00:00Z','COLLECTION_CONTACT',{'delivery':'DEAD','dnr_until':None}),ev('E4','2026-09-18T08:00:00Z','ROUTE_REPAIRED',{})); self.assertEqual(compile_ledger(s)['payload']['claims'][0]['next_action'],'WAIT_REPLY')
 def test_conflicting_event_economics_rejected(self):
  s=copy.deepcopy(BASE); s['claims'][0]['events'][1]['data']['amount']='1251.00'
  with self.assertRaisesRegex(CollectionError,'conflicting economics'): compile_ledger(s)
 def test_illegal_transition_rejected(self):
  s=add(BASE,ev('E3','2026-09-18T08:00:00Z','SETTLED_CASH',{'amount':'1250.00','instrument':'USD','settlement_ref':'BANK-1'}))
  with self.assertRaisesRegex(CollectionError,'illegal transition'): compile_ledger(s)
 def test_duplicate_json_key_rejected(self):
  with self.assertRaisesRegex(CollectionError,'duplicate JSON key'): load_json_bytes(b'{"schema":"a","schema":"b"}')
 def test_json_numeric_and_bool_aliases_rejected(self):
  with self.assertRaises(CollectionError): load_json_bytes(b'{"v":1}')
  with self.assertRaises(CollectionError): load_json_bytes(b'{"v":1.5}')
  with self.assertRaises(CollectionError): load_json_bytes(b'{"v":NaN}')
  with self.assertRaises(CollectionError): load_json_bytes(b'{"v":true}')
 def test_duplicate_claim_identity_rejected(self):
  s=copy.deepcopy(BASE); second=copy.deepcopy(s['claims'][0]); second['claim_id']='C2'; second['events'][0]['event_id']='X1'; second['events'][1]['event_id']='X2'; s['claims'].append(second)
  with self.assertRaisesRegex(CollectionError,'duplicate counterparty/work_ref'): compile_ledger(s)
 def test_input_order_invariance(self):
  s=add(BASE,ev('E3','2026-09-18T08:00:00Z','COLLECTION_RELEASED',{'not_before':'2026-09-18T08:00:00Z','expires_at':'2026-09-19T08:00:00Z'})); a=compile_ledger(s); t=copy.deepcopy(s); t['claims'][0]['events'].reverse(); b=compile_ledger(t); self.assertEqual(a,b)
 def test_report_tamper_rejected(self):
  r=compile_ledger(BASE); bad=copy.deepcopy(r); bad['payload']['claims'][0]['next_action']='DONE'
  with self.assertRaisesRegex(CollectionError,'verification failed'): verify_ledger(BASE,bad)
 def test_artifact_bundle_deterministic(self):
  raw=(json.dumps(BASE,sort_keys=True,separators=(',',':'))+'\n').encode(); self.assertEqual(artifact_bundle(raw),artifact_bundle(raw)); self.assertIn(b'no message is authorized',artifact_bundle(raw)['queue.md'])
 def test_cli_compile_verify_and_existing_destination(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as td:
   src=Path(td)/'source.json'; src.write_text(json.dumps(BASE,separators=(',',':'))); out=Path(td)/'out'
   p=subprocess.run([sys.executable,'-m','tools.revenue_collection_desk.cli','compile',str(src),str(out)],cwd=root,capture_output=True,text=True); self.assertEqual(p.returncode,0,p.stderr)
   q=subprocess.run([sys.executable,'-m','tools.revenue_collection_desk.cli','verify',str(src),str(out)],cwd=root,capture_output=True,text=True); self.assertEqual(q.returncode,0,q.stderr)
   z=subprocess.run([sys.executable,'-m','tools.revenue_collection_desk.cli','compile',str(src),str(out)],cwd=root,capture_output=True,text=True); self.assertEqual(z.returncode,2)

if __name__=='__main__': unittest.main()
