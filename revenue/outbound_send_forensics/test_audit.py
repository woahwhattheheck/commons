import copy,unittest
from revenue.outbound_connector_lease.key import compile_document
from revenue.outbound_send_forensics.audit import *
SCHEMA='outbound-connector-lease/v1'
def seam(): return {'schema':SCHEMA,'buyer_scope':'Example.COM.','opportunity':{'kind':'external','authority':'Issuer.EXAMPLE.','id':'RFP-04254'}}
def send(event='msg-1',when='2026-09-14T01:20:00Z',authority='provider-receipt',status='sent',receipt='a'*64,provider='gmail'): return {'provider':provider,'event_id':event,'sent_at':when,'authority':authority,'status':status,'receipt_sha256':receipt}
def lease(s=None,when='2026-09-14T01:19:00Z',authority='github-create-result',result='created',branch=None,receipt='b'*64,base='c'*40,repository=CANONICAL_LEASE_REPOSITORY):
 s=s or seam(); return {'repository_full_name':repository,'branch':branch or compile_document(s)['branch'],'created_at':when,'authority':authority,'result':result,'base_sha':base,'receipt_sha256':receipt}
def record(rid='r1',event='msg-1',s=None,send_kwargs=None,lease_value='default'):
 s=copy.deepcopy(s or seam()); return {'record_id':rid,'seam':s,'send':send(event=event,**(send_kwargs or {})),'lease_create':lease(s) if lease_value=='default' else lease_value}
def doc(*rows): return {'schema':'outbound-send-forensics/v1','records':list(rows)}
class AuditTests(unittest.TestCase):
 def one(self,r): return audit_document(doc(r))['receipts'][0]
 def test_protected_binds_canonical_repository(self):
  o=self.one(record()); self.assertEqual(o['classification'],CLASS_PROTECTED); self.assertEqual(o['expected_lease_repository'],CANONICAL_LEASE_REPOSITORY); self.assertEqual(o['lease_repository_full_name'],CANONICAL_LEASE_REPOSITORY); self.assertTrue(o['dnr'])
 def test_noncanonical_repository_is_untrusted_even_with_genuine_create_shape(self):
  o=self.one(record(lease_value=lease(repository='woahwhattheheck/commons-fork'))); self.assertEqual(o['classification'],CLASS_UNTRUSTED); self.assertIn('canonical repository',o['reasons'][0]); self.assertTrue(o['dnr'])
 def test_repository_normalization_and_validation(self):
  self.assertEqual(self.one(record(lease_value=lease(repository=' WoahWhatTheHeck/Commons ')))['classification'],CLASS_PROTECTED)
  self.assertEqual(self.one(record(lease_value=lease(repository='WoahWhatTheHeck/Other')))['classification'],CLASS_UNTRUSTED)
  for v in (True,'commons','owner/repo/extra','https://github.com/woahwhattheheck/commons'):
   with self.subTest(v=v),self.assertRaisesRegex(ForensicsError,'repository'): self.one(record(lease_value=lease(repository=v)))
 def test_receipt_hash_binds_repository_identity(self):
  a=self.one(record()); b=self.one(record(lease_value=lease(repository='woahwhattheheck/commons-fork'))); self.assertNotEqual(a['receipt_sha256'],b['receipt_sha256'])
 def test_chronology_equal_and_later_are_post_send(self):
  for t in ('2026-09-14T01:20:00Z','2026-09-14T01:21:00Z'):
   with self.subTest(t=t): self.assertEqual(self.one(record(lease_value=lease(when=t)))['classification'],CLASS_POST_SEND)
 def test_missing_mismatch_and_noncreate(self):
  self.assertEqual(self.one(record(lease_value=None))['classification'],CLASS_MISSING)
  self.assertEqual(self.one(record(lease_value=lease(branch='outbound-connector-lease/v1/'+'0'*64)))['classification'],CLASS_MISMATCH)
  for result in ('exists','ambiguous','failed'):
   with self.subTest(result=result): self.assertEqual(self.one(record(lease_value=lease(result=result)))['classification'],CLASS_UNTRUSTED)
 def test_caller_or_ambiguous_evidence_untrusted(self):
  self.assertEqual(self.one(record(lease_value=lease(authority='caller-assertion')))['classification'],CLASS_UNTRUSTED)
  self.assertEqual(self.one(record(send_kwargs={'authority':'caller-assertion'}))['classification'],CLASS_UNTRUSTED)
  self.assertEqual(self.one(record(send_kwargs={'status':'ambiguous'}))['classification'],CLASS_UNTRUSTED)
 def test_timestamps_are_strict_and_normalized(self):
  o=self.one(record(send_kwargs={'when':'2026-09-13T21:20:00-04:00'},lease_value=lease(when='2026-09-14T01:19:59+00:00'))); self.assertEqual(o['classification'],CLASS_PROTECTED); self.assertEqual(o['send_at_utc'],'2026-09-14T01:20:00.000000Z')
  for t in ('2026-09-14T01:20:00','2026-09-14 01:20:00+00:00'):
   with self.subTest(t=t),self.assertRaisesRegex(ForensicsError,'strict RFC3339'): self.one(record(send_kwargs={'when':t}))
 def test_malformed_branch_hash_and_types_rejected(self):
  b=lease(); b['branch']='outbound-connector-lease/v1/not-a-hash'
  with self.assertRaisesRegex(ForensicsError,'64-lowercase-hex'): self.one(record(lease_value=b))
  with self.assertRaisesRegex(ForensicsError,'64 lowercase hex'): self.one(record(send_kwargs={'receipt':'A'*64}))
  b=lease(); b['base_sha']='c'*39
  with self.assertRaisesRegex(ForensicsError,'40 lowercase hex'): self.one(record(lease_value=b))
  r=record(); r['send']['event_id']=True
  with self.assertRaisesRegex(ForensicsError,'must be a string'): self.one(r)
 def test_exact_fields_and_provider_registry(self):
  r=record(); r['send']['subject']='x'
  with self.assertRaisesRegex(ForensicsError,'extra=subject'): self.one(r)
  r=record(); r['lease_create']['repository_url']='x'
  with self.assertRaisesRegex(ForensicsError,'extra=repository_url'): self.one(r)
  with self.assertRaisesRegex(ForensicsError,'must be one of'): self.one(record(send_kwargs={'provider':'email'}))
 def test_strict_json_and_empty_batch(self):
  with self.assertRaisesRegex(ForensicsError,'duplicate JSON key'): audit_json('{"schema":"outbound-send-forensics/v1","schema":"outbound-send-forensics/v1","records":[]}')
  with self.assertRaisesRegex(ForensicsError,'non-finite'): audit_json('{"schema":"outbound-send-forensics/v1","records":NaN}')
  with self.assertRaisesRegex(ForensicsError,'non-empty array'): audit_document(doc())
 def test_duplicate_ids_and_provider_events_rejected(self):
  with self.assertRaisesRegex(ForensicsError,'duplicate record_id'): audit_document(doc(record(rid='Case-A',event='a'),record(rid='case-a',event='b')))
  with self.assertRaisesRegex(ForensicsError,'duplicate provider event'): audit_document(doc(record(rid='a',event='same'),record(rid='b',event='same')))
  with self.assertRaisesRegex(ForensicsError,'contradictory duplicate provider event'): audit_document(doc(record(rid='a',event='same'),record(rid='b',event='same',send_kwargs={'when':'2026-09-14T01:21:00Z'})))
 def test_distinct_events_same_seam_are_incident(self):
  o=audit_document(doc(record(rid='a',event='e1'),record(rid='b',event='e2'))); self.assertEqual(o['summary']['duplicate_seams'],1); self.assertEqual(o['summary']['duplicate_send_records'],2); self.assertTrue(all(x['batch_flags']==[DUPLICATE_FLAG] for x in o['receipts']))
 def test_order_independent_and_deterministic(self):
  a=record(rid='a',event='e1'); b=record(rid='b',event='e2'); x=audit_document(doc(a,b)); y=audit_document(doc(b,a)); self.assertEqual(x['batch_sha256'],y['batch_sha256']); self.assertEqual(x['receipts'],y['receipts']); self.assertEqual(x,audit_document(doc(a,b)))
 def test_seam_normalization_uses_landed_compiler(self):
  s1=seam(); s2=copy.deepcopy(s1); s2['buyer_scope']='example.com'; s2['opportunity']['authority']='issuer.example'; s2['opportunity']['id']='rfp-04254'; self.assertEqual(compile_document(s1)['branch'],compile_document(s2)['branch']); self.assertEqual(self.one(record(s=s1,lease_value=lease(s2)))['classification'],CLASS_PROTECTED)
if __name__=='__main__': unittest.main()
