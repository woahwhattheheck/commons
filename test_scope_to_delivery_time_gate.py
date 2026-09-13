import copy
import hashlib
import inspect
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from host import scope_to_delivery as canonical_scope
from host import scope_to_delivery_time_gate as gate


def z(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def agreement():
    doc={
      'schema_version':'commons-scope-agreement/v1','kind':'SCOPE_AGREEMENT',
      'agreement_id':'agr-temporal-hostile-20260913-0001','sku_id':'production-survival-sprint',
      'quote':{'currency':'USD','amount':'15000.00'},
      'window':{'start':'2026-09-13T10:00:00Z','end':'2026-09-13T12:00:00Z','timezone':'UTC'},
      'buyer_ref':'buyer_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      'intake_sentence':'Synthetic exact-byte temporal authority fixture.',
      'acceptance_rows':[{'id':'happy-path','given':'Synthetic input','when':'Run in window','then':'Observe exact result','evidence_required':['public_ref','sha256']}],
      'exclusions':['credentials','private-data'],'refund_choice':'REFUND_IF_MISS',
      'written_acceptance':{'status':'PRESENT','attestation':'AUTHORIZED_OPERATOR_VERIFIED_EXACT_TERMS_ACCEPTANCE','terms_digest':'0'*64,'public_ref':'revenue/scope_to_delivery/fixtures/synthetic-acceptance.txt','accepted_at':'2026-09-13T09:30:00Z'}
    }
    doc['written_acceptance']['terms_digest']=canonical_scope.terms_digest(doc)
    return doc


def observations(*times: str):
    return {'schema_version':'commons-scope-observations/v1','kind':'EXECUTION_OBSERVATIONS','agreement_id':'agr-temporal-hostile-20260913-0001','observations':[
        {'observation_id':f'obs-{i:02d}-temporal','kind':'WORK_STARTED','row_id':None,'result':'UNMEASURED','public_ref':None,'sha256':None,'observed_at':when,'note':'Synthetic chronology marker.'}
        for i,when in enumerate(times,1)
    ]}


def raw(v,*,pretty=False):
    return json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2 if pretty else None,separators=None if pretty else (',',':')).encode()


def project(doc,obs=None):
    return canonical_scope.compose_project(doc, canonical_scope.load_json(canonical_scope.DEFAULT_CATALOG), canonical_scope.load_bindings(canonical_scope.DEFAULT_BINDINGS), obs, None)


_AUTO=object()
def eval_bytes(doc=None,obs=None,*,as_of='2026-09-13T11:00:00Z',canonical_project=_AUTO):
    doc=agreement() if doc is None else doc
    if canonical_project is _AUTO: canonical_project=project(doc,obs)
    return gate.evaluate_bytes(raw(doc),None if obs is None else raw(obs),as_of=z(as_of),canonical_project=canonical_project)


class Tests(unittest.TestCase):
    def test_ready_requires_exact_bytes_and_bound_canonical_project(self):
        obs=observations('2026-09-13T10:15:00Z'); out=eval_bytes(obs=obs)
        self.assertEqual(out['state'],'TEMPORAL_PREREQUISITE_READY'); self.assertTrue(out['current_work_authorized'])
        self.assertTrue(out['raw_byte_provenance_verified']); self.assertTrue(out['canonical_scope_validated']); self.assertTrue(out['canonical_project_bound'])
        self.assertEqual(gate.verify_project_binding(project(agreement(),obs),out)['valid'],True)
        for k in ('external_action_authorized','payment_authorized','delivery_claim_authorized','revenue_authorized'): self.assertFalse(out[k])

    def test_exact_bytes_without_project_hold(self):
        out=eval_bytes(canonical_project=None)
        self.assertEqual(out['state'],'HOLD_CANONICAL_PROJECT_UNBOUND'); self.assertFalse(out['current_work_authorized'])
        self.assertTrue(out['canonical_scope_validated']); self.assertFalse(out['canonical_project_bound'])

    def test_parsed_path_fail_closed(self):
        out=gate.evaluate(agreement(),observations('2026-09-13T10:15:00Z'),as_of=z('2026-09-13T11:00:00Z'))
        self.assertEqual(out['state'],'HOLD_RAW_PROVENANCE_UNVERIFIED'); self.assertFalse(out['current_work_authorized']); self.assertFalse(out['canonical_scope_validated'])
        self.assertNotIn('agreement_raw_sha256',inspect.signature(gate.evaluate).parameters)

    def test_partial_same_id_temporal_b_is_rejected_by_canonical_scope(self):
        partial={'schema_version':'commons-scope-agreement/v1','kind':'SCOPE_AGREEMENT','agreement_id':agreement()['agreement_id'],'window':agreement()['window'],'written_acceptance':agreement()['written_acceptance']}
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'canonical scope'):
            gate.evaluate_bytes(raw(partial),None,as_of=z('2026-09-13T11:00:00Z'),canonical_project=project(agreement()))

    def test_complete_same_id_agreement_a_vs_temporal_b_project_mismatch_rejected(self):
        a=agreement(); pa=project(a)
        b=copy.deepcopy(a); b['window']={'start':'2026-09-13T10:30:00Z','end':'2026-09-13T11:30:00Z','timezone':'UTC'}; b['written_acceptance']['terms_digest']=canonical_scope.terms_digest(b)
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'does not bind'):
            eval_bytes(doc=b,as_of='2026-09-13T11:00:00Z',canonical_project=pa)
        self.assertTrue(eval_bytes(doc=b,as_of='2026-09-13T11:00:00Z',canonical_project=project(b))['current_work_authorized'])

    def test_same_agreement_observation_a_vs_b_project_mismatch_rejected(self):
        doc=agreement(); oa=observations('2026-09-13T10:15:00Z'); ob=observations('2026-09-13T10:25:00Z')
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'does not bind'):
            eval_bytes(doc=doc,obs=ob,canonical_project=project(doc,oa))
        self.assertTrue(eval_bytes(doc=doc,obs=ob,canonical_project=project(doc,ob))['current_work_authorized'])

    def test_verify_project_binding_rejects_other_project(self):
        a=agreement(); out=eval_bytes(doc=a)
        b=copy.deepcopy(a); b['window']['end']='2026-09-13T11:45:00Z'; b['written_acceptance']['terms_digest']=canonical_scope.terms_digest(b)
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'different artifacts'):
            gate.verify_project_binding(project(b),out)

    def test_expired_holds_but_historical_admissible(self):
        out=eval_bytes(obs=observations('2026-09-13T10:15:00Z','2026-09-13T11:50:00Z'),as_of='2026-09-13T13:00:00Z')
        self.assertEqual(out['state'],'HOLD_WINDOW_EXPIRED'); self.assertFalse(out['current_work_authorized']); self.assertTrue(out['historical_evidence_temporally_admissible'])

    def test_aug28_historical_hold(self):
        doc=agreement(); doc['agreement_id']='agr-synthetic-production-survival-20260828-01'; doc['window']={'start':'2026-08-28T13:00:00-04:00','end':'2026-08-28T21:00:00-04:00','timezone':'America/New_York'}; doc['written_acceptance']['accepted_at']='2026-08-28T12:00:00-04:00'; doc['written_acceptance']['terms_digest']=canonical_scope.terms_digest(doc)
        obs=observations('2026-08-28T13:05:00-04:00','2026-08-28T15:00:00-04:00'); obs['agreement_id']=doc['agreement_id']
        out=eval_bytes(doc=doc,obs=obs,as_of='2026-09-13T10:00:00Z')
        self.assertEqual(out['state'],'HOLD_WINDOW_EXPIRED'); self.assertFalse(out['current_work_authorized'])

    def test_window_not_started(self): self.assertEqual(eval_bytes(as_of='2026-09-13T09:45:00Z')['state'],'HOLD_WINDOW_NOT_STARTED')

    def test_nonpresent_hold(self):
        doc=agreement(); doc['written_acceptance']={'status':'ABSENT','attestation':None,'terms_digest':canonical_scope.terms_digest(doc),'public_ref':None,'accepted_at':None}; doc['written_acceptance']['terms_digest']=canonical_scope.terms_digest(doc)
        self.assertEqual(eval_bytes(doc=doc)['state'],'HOLD_NO_PRESENT_ACCEPTANCE')

    def test_future_acceptance_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'acceptance is in'): eval_bytes(as_of='2026-09-13T09:00:00Z')

    def test_acceptance_after_window_rejected(self):
        doc=agreement(); doc['written_acceptance']['accepted_at']='2026-09-13T12:01:00Z'; doc['written_acceptance']['terms_digest']=canonical_scope.terms_digest(doc)
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'after the contracted window'): eval_bytes(doc=doc,as_of='2026-09-13T13:00:00Z')

    def test_observation_before_acceptance(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'predates written acceptance'): eval_bytes(obs=observations('2026-09-13T09:00:00Z'))

    def test_observation_after_window(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'after contracted work window'): eval_bytes(obs=observations('2026-09-13T12:00:01Z'),as_of='2026-09-13T13:00:00Z')

    def test_future_observation(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError,"verifier's future"): eval_bytes(obs=observations('2026-09-13T11:30:00Z'))

    def test_duplicate_json_key_rejected(self):
        good=raw(agreement()); bad=good[:-1]+b',"agreement_id":"other"}'
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'duplicate JSON key'): gate.evaluate_bytes(bad,None,as_of=z('2026-09-13T11:00:00Z'),canonical_project=None)

    def test_same_json_different_bytes_raw_distinct_project_same(self):
        doc=agreement(); obs=observations('2026-09-13T10:15:00Z'); p=project(doc,obs)
        compact=gate.evaluate_bytes(raw(doc),raw(obs),as_of=z('2026-09-13T11:00:00Z'),canonical_project=p)
        pretty=gate.evaluate_bytes(raw(doc,pretty=True),raw(obs,pretty=True),as_of=z('2026-09-13T11:00:00Z'),canonical_project=p)
        self.assertEqual(compact['agreement_canonical_sha256'],pretty['agreement_canonical_sha256']); self.assertNotEqual(compact['agreement_raw_sha256'],pretty['agreement_raw_sha256']); self.assertEqual(compact['canonical_project_sha256'],pretty['canonical_project_sha256'])

    def test_internal_raw_hashes_cannot_be_overridden(self):
        a=raw(agreement()); bdoc=agreement(); bdoc['agreement_id']='agr-temporal-hostile-20260913-9999'; b=raw(bdoc)
        out=gate.evaluate_bytes(a,None,as_of=z('2026-09-13T11:00:00Z'),canonical_project=project(agreement()))
        self.assertEqual(out['agreement_raw_sha256'],hashlib.sha256(a).hexdigest()); self.assertNotEqual(out['agreement_raw_sha256'],hashlib.sha256(b).hexdigest())

    def test_nonbytes_oversize(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'exact bytes'): gate.evaluate_bytes(bytearray(raw(agreement())),None,as_of=z('2026-09-13T11:00:00Z'))
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'exceeds'): gate.evaluate_bytes(b' '*(gate.MAX_INPUT_BYTES+1),None,as_of=z('2026-09-13T11:00:00Z'))

    @unittest.skipUnless(hasattr(os,'O_NOFOLLOW'),'requires O_NOFOLLOW')
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); real=root/'a.json'; link=root/'l.json'; real.write_text(json.dumps(agreement())); link.symlink_to(real)
            with self.assertRaisesRegex(gate.TemporalAuthorityError,'non-symlink'): gate.read_plain_bytes(link,'agreement')

    @unittest.skipUnless(hasattr(os,'O_NOFOLLOW'),'requires O_NOFOLLOW')
    def test_file_byte_hash_exact(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'a.json'; exact=raw(agreement(),pretty=True)+b'\n'; path.write_bytes(exact); read=gate.read_plain_bytes(path,'agreement')
            out=gate.evaluate_bytes(read,None,as_of=z('2026-09-13T11:00:00Z'),canonical_project=project(agreement()))
            self.assertEqual(out['agreement_raw_sha256'],hashlib.sha256(exact).hexdigest())

    def test_observation_before_window_rejected(self):
        doc=agreement(); doc['written_acceptance']['accepted_at']='2026-09-13T09:00:00Z'
        with self.assertRaisesRegex(gate.TemporalAuthorityError,'predates contracted work window'):
            eval_bytes(doc=doc,obs=observations('2026-09-13T09:45:00Z'))

    def test_receipt_is_deterministic_and_project_bound(self):
        doc=agreement(); obs=observations('2026-09-13T10:15:00Z'); p=project(doc,obs)
        first=gate.evaluate_bytes(raw(doc),raw(obs),as_of=z('2026-09-13T11:00:00Z'),canonical_project=p)
        second=gate.evaluate_bytes(raw(copy.deepcopy(doc)),raw(copy.deepcopy(obs)),as_of=z('2026-09-13T11:00:00Z'),canonical_project=copy.deepcopy(p))
        self.assertEqual(first,second)
        self.assertEqual(first['canonical_project_sha256'],gate.digest(p))

    @unittest.skipUnless(hasattr(os,'O_NOFOLLOW'),'requires O_NOFOLLOW')
    def test_cli_requires_matching_project_for_ready_exit(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); doc=agreement(); obs=observations('2026-09-13T10:15:00Z'); p=project(doc,obs)
            ap=root/'a.json'; op=root/'o.json'; pp=root/'p.json'
            ap.write_bytes(raw(doc)); op.write_bytes(raw(obs)); pp.write_bytes(raw(p))
            cli=Path(gate.__file__)
            bad=copy.deepcopy(p); bad['agreement_id']='agr-other-project-20260913'
            bp=root/'bad.json'; bp.write_bytes(raw(bad))
            result=subprocess.run([sys.executable,str(cli),'--agreement',str(ap),'--observations',str(op),'--project',str(bp)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('HOLD_INVALID_TEMPORAL_EVIDENCE',result.stdout)


if __name__=='__main__': unittest.main()
