import copy,json,unittest
from revenue.outbound_connector_lease.key import compile_document
from revenue.outbound_send_forensics.audit import (
    CLASS_MISMATCH,CLASS_MISSING,CLASS_POST_SEND,CLASS_PROTECTED,CLASS_UNTRUSTED,
    DUPLICATE_FLAG,ForensicsError,audit_document,audit_json,
)

SCHEMA='outbound-connector-lease/v1'

def seam():
    return {'schema':SCHEMA,'buyer_scope':'Example.COM.','opportunity':{'kind':'external','authority':'Issuer.EXAMPLE.','id':'RFP-04254'}}

def send(event='msg-1',when='2026-09-14T01:20:00Z',authority='provider-receipt',status='sent',receipt='a'*64,provider='gmail'):
    return {'provider':provider,'event_id':event,'sent_at':when,'authority':authority,'status':status,'receipt_sha256':receipt}

def lease(s=None,when='2026-09-14T01:19:00Z',authority='github-create-result',result='created',branch=None,receipt='b'*64,base='c'*40):
    s=s or seam(); expected=compile_document(s)['branch']
    return {'branch':branch or expected,'created_at':when,'authority':authority,'result':result,'base_sha':base,'receipt_sha256':receipt}

def record(rid='r1',event='msg-1',s=None,send_kwargs=None,lease_value='default'):
    s=copy.deepcopy(s or seam()); sk=send_kwargs or {}
    lv=lease(s) if lease_value=='default' else lease_value
    return {'record_id':rid,'seam':s,'send':send(event=event,**sk),'lease_create':lv}

def doc(*records): return {'schema':'outbound-send-forensics/v1','records':list(records)}

class AuditTests(unittest.TestCase):
    def one(self,r): return audit_document(doc(r))['receipts'][0]

    def test_protected_requires_strictly_earlier_matching_create(self):
        out=self.one(record()); self.assertEqual(out['classification'],CLASS_PROTECTED); self.assertTrue(out['dnr']); self.assertEqual(out['same_seam_send_count'],1)

    def test_equal_timestamp_is_post_send_violation(self):
        r=record(lease_value=lease(when='2026-09-14T01:20:00Z')); self.assertEqual(self.one(r)['classification'],CLASS_POST_SEND)

    def test_later_create_is_post_send_violation(self):
        r=record(lease_value=lease(when='2026-09-14T01:21:00Z')); self.assertEqual(self.one(r)['classification'],CLASS_POST_SEND)

    def test_missing_lease_is_incident_and_dnr(self):
        out=self.one(record(lease_value=None)); self.assertEqual(out['classification'],CLASS_MISSING); self.assertTrue(out['dnr']); self.assertIsNone(out['lease_branch'])

    def test_wrong_canonical_branch_is_mismatch(self):
        r=record(lease_value=lease(branch='outbound-connector-lease/v1/'+'0'*64)); self.assertEqual(self.one(r)['classification'],CLASS_MISMATCH)

    def test_branch_existence_or_noncreate_result_is_not_proof(self):
        for result in ('exists','ambiguous','failed'):
            with self.subTest(result=result):
                r=record(lease_value=lease(result=result)); self.assertEqual(self.one(r)['classification'],CLASS_UNTRUSTED)

    def test_caller_asserted_lease_is_not_authority(self):
        r=record(lease_value=lease(authority='caller-assertion')); self.assertEqual(self.one(r)['classification'],CLASS_UNTRUSTED)

    def test_caller_asserted_send_is_not_authority(self):
        r=record(send_kwargs={'authority':'caller-assertion'}); self.assertEqual(self.one(r)['classification'],CLASS_UNTRUSTED)

    def test_ambiguous_send_is_untrusted_and_dnr(self):
        out=self.one(record(send_kwargs={'status':'ambiguous'})); self.assertEqual(out['classification'],CLASS_UNTRUSTED); self.assertTrue(out['dnr'])

    def test_timezone_offsets_are_compared_as_instants(self):
        r=record(send_kwargs={'when':'2026-09-13T21:20:00-04:00'},lease_value=lease(when='2026-09-14T01:19:59+00:00'))
        out=self.one(r); self.assertEqual(out['classification'],CLASS_PROTECTED); self.assertEqual(out['send_at_utc'],'2026-09-14T01:20:00.000000Z')

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ForensicsError,'strict RFC3339'):
            self.one(record(send_kwargs={'when':'2026-09-14T01:20:00'}))

    def test_space_separated_iso_timestamp_is_rejected_as_non_rfc3339(self):
        with self.assertRaisesRegex(ForensicsError,'strict RFC3339'):
            self.one(record(send_kwargs={'when':'2026-09-14 01:20:00+00:00'}))

    def test_malformed_branch_rejected_before_classification(self):
        bad=lease(); bad['branch']='outbound-connector-lease/v1/not-a-hash'
        with self.assertRaisesRegex(ForensicsError,'64-lowercase-hex'): self.one(record(lease_value=bad))

    def test_uppercase_or_wrong_length_hash_rejected(self):
        with self.assertRaisesRegex(ForensicsError,'64 lowercase hex'):
            self.one(record(send_kwargs={'receipt':'A'*64}))
        bad=lease();bad['base_sha']='c'*39
        with self.assertRaisesRegex(ForensicsError,'40 lowercase hex'): self.one(record(lease_value=bad))

    def test_extra_fields_fail_closed_at_every_boundary(self):
        r=record(); r['send']['subject']='variant'
        with self.assertRaisesRegex(ForensicsError,'extra=subject'): self.one(r)
        r=record(); r['seam']['price']=2500
        with self.assertRaisesRegex(ForensicsError,'record.seam invalid'): self.one(r)

    def test_unsupported_provider_rejected(self):
        with self.assertRaisesRegex(ForensicsError,'must be one of'):
            self.one(record(send_kwargs={'provider':'email'}))

    def test_boolean_event_id_rejected(self):
        r=record();r['send']['event_id']=True
        with self.assertRaisesRegex(ForensicsError,'must be a string'): self.one(r)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        raw='{"schema":"outbound-send-forensics/v1","schema":"outbound-send-forensics/v1","records":[]}'
        with self.assertRaisesRegex(ForensicsError,'duplicate JSON key'): audit_json(raw)
        with self.assertRaisesRegex(ForensicsError,'non-finite'): audit_json('{"schema":"outbound-send-forensics/v1","records":NaN}')

    def test_empty_batch_rejected(self):
        with self.assertRaisesRegex(ForensicsError,'non-empty array'): audit_document(doc())

    def test_duplicate_record_id_rejected_after_normalization(self):
        r1=record(rid='Case-A',event='e1');r2=record(rid='case-a',event='e2')
        with self.assertRaisesRegex(ForensicsError,'duplicate record_id'): audit_document(doc(r1,r2))

    def test_duplicate_provider_event_rejected(self):
        r1=record(rid='r1',event='same');r2=record(rid='r2',event='same')
        with self.assertRaisesRegex(ForensicsError,'duplicate provider event'): audit_document(doc(r1,r2))

    def test_contradictory_duplicate_provider_event_rejected(self):
        r1=record(rid='r1',event='same');r2=record(rid='r2',event='same',send_kwargs={'when':'2026-09-14T01:21:00Z'})
        with self.assertRaisesRegex(ForensicsError,'contradictory duplicate provider event'): audit_document(doc(r1,r2))

    def test_distinct_events_same_seam_are_duplicate_send_incident(self):
        out=audit_document(doc(record(rid='r1',event='msg-1'),record(rid='r2',event='msg-2')))
        self.assertEqual(out['summary']['duplicate_seams'],1);self.assertEqual(out['summary']['duplicate_send_records'],2);self.assertEqual(out['incident_seams'][0]['send_count'],2)
        for r in out['receipts']:
            self.assertEqual(r['batch_flags'],[DUPLICATE_FLAG]);self.assertEqual(r['same_seam_send_count'],2)

    def test_input_order_does_not_change_batch_receipt(self):
        a=record(rid='a',event='e-a');b=record(rid='b',event='e-b')
        one=audit_document(doc(a,b));two=audit_document(doc(b,a))
        self.assertEqual(one['batch_sha256'],two['batch_sha256']);self.assertEqual(one['receipts'],two['receipts'])

    def test_seam_normalization_uses_landed_key_compiler(self):
        s1=seam();s2=copy.deepcopy(s1);s2['buyer_scope']='example.com';s2['opportunity']['authority']='issuer.example';s2['opportunity']['id']='rfp-04254'
        self.assertEqual(compile_document(s1)['branch'],compile_document(s2)['branch'])
        out=self.one(record(s=s1,lease_value=lease(s2)));self.assertEqual(out['classification'],CLASS_PROTECTED)

    def test_receipt_and_batch_hashes_are_self_consistent_and_deterministic(self):
        out=audit_document(doc(record())); receipt=out['receipts'][0]
        self.assertRegex(receipt['receipt_sha256'],r'^[0-9a-f]{64}$');self.assertRegex(out['batch_sha256'],r'^[0-9a-f]{64}$')
        self.assertEqual(out,audit_document(doc(record())))

if __name__=='__main__': unittest.main()
