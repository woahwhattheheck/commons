from __future__ import annotations
import copy, importlib.util, json, tempfile, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('rcap_validate',HERE/'validate_recovery.py'); mod=importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(mod)
def load(n): return json.loads((HERE/n).read_text(encoding='utf-8'))
class Tests(unittest.TestCase):
    def setUp(self): self.pub=load('public_opportunity_20260917.json'); self.truth=load('proposal_truth_20260917.json')
    def pub_bad(self,f):
        p=copy.deepcopy(self.pub); f(p)
        with self.assertRaises(mod.PacketError): mod.validate_public(p)
    def truth_bad(self,f):
        p=copy.deepcopy(self.truth); f(p)
        with self.assertRaises(mod.PacketError): mod.validate_truth(p,HERE)
    def test_baseline(self):
        self.assertIn('EXACT_ROUTE_FIRST_PARTY_RESOLVED',mod.validate_public(self.pub))
        self.assertIn('HISTORICAL_PDF_INELIGIBLE_REGEN_REQUIRED',mod.validate_truth(self.truth,HERE))
        self.assertEqual(mod.validate_public_surface(HERE),['NO_PUBLIC_COMMONS_BACKLINK'])
    def test_duplicate_key(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json'; p.write_text('{"schema_version":2,"schema_version":2}',encoding='utf-8')
            with self.assertRaises(mod.PacketError): mod.load_json(p)
    def test_bool_int_schema_alias(self): self.pub_bad(lambda p:p.__setitem__('schema_version',True))
    def test_due_drift(self): self.pub_bad(lambda p:p['public_time_gates'].__setitem__('proposal_due','2026-10-05'))
    def test_user_scale_drift(self): self.pub_bad(lambda p:p['public_scale'].__setitem__('active_dcs_users_low',1))
    def test_weight_drift(self): self.pub_bad(lambda p:p['evaluation_weights_percent'].__setitem__('approach',24))
    def test_us_condition_weakened(self): self.pub_bad(lambda p:p['hard_conditions'].__setitem__('respondent_primary_place_of_business_in_us',False))
    def test_coi_condition_weakened(self): self.pub_bad(lambda p:p['hard_conditions'].__setitem__('professional_indemnity_or_liability_coi_required_at_award',False))
    def test_wrong_route_rejected(self): self.pub_bad(lambda p:p['submission'].__setitem__('exact_email','griffin@example.org'))
    def test_route_source_drift_rejected(self): self.pub_bad(lambda p:p['submission'].__setitem__('route_source_url','https://example.org/'))
    def test_route_resolution_cannot_authorize_contact(self): self.pub_bad(lambda p:p['authority'].__setitem__('buyer_contact_authorized',True))
    def test_submission_escalation(self): self.pub_bad(lambda p:p['authority'].__setitem__('proposal_submitted',True))
    def test_award_escalation(self): self.pub_bad(lambda p:p['authority'].__setitem__('award',True))
    def test_revenue_escalation(self): self.pub_bad(lambda p:p['authority'].__setitem__('recognized_revenue',True))
    def test_bool_int_base_price_alias(self): self.truth_bad(lambda p:p['base_offer'].__setitem__('amount_minor',True))
    def test_base_price_drift(self): self.truth_bad(lambda p:p['base_offer'].__setitem__('amount_minor',2450001))
    def test_discovery_count_drift(self): self.truth_bad(lambda p:p['discovery'].__setitem__('stakeholder_sessions',5))
    def test_schedule_drift(self): self.truth_bad(lambda p:p['schedule'].__setitem__('estimated_weeks',5))
    def test_optional_folded_into_base(self): self.truth_bad(lambda p:p['optional_service'].__setitem__('included_in_base',True))
    def test_optional_acceptance_rejected(self): self.truth_bad(lambda p:p['optional_service'].__setitem__('accepted',True))
    def test_pdf_hash_drift(self): self.truth_bad(lambda p:p['artifacts'].__setitem__('pdf_sha256','0'*64))
    def test_pdf_page_drift(self): self.truth_bad(lambda p:p['artifacts'].__setitem__('pdf_pages',5))
    def test_historical_pdf_cannot_be_submission_eligible(self): self.truth_bad(lambda p:p['artifacts'].__setitem__('submission_eligible',True))
    def test_pdf_regeneration_cannot_be_suppressed(self): self.truth_bad(lambda p:p['artifacts'].__setitem__('regeneration_required',False))
    def test_invented_reference_rejected(self): self.truth_bad(lambda p:p['experience_truth'].__setitem__('client_references_invented',True))
    def test_commons_work_sample_rejected(self): self.truth_bad(lambda p:p['experience_truth'].__setitem__('public_work_sample','https://github.com/woahwhattheheck/commons'))
    def test_commons_backlink_claim_rejected(self): self.truth_bad(lambda p:p['experience_truth'].__setitem__('public_commons_backlink_present',True))
    def test_wrong_truth_recipient_rejected(self): self.truth_bad(lambda p:p['submission'].__setitem__('exact_recipient','x@example.org'))
    def test_truth_route_source_drift_rejected(self): self.truth_bad(lambda p:p['submission'].__setitem__('route_source_url','https://example.org/'))
    def test_fake_muse_clear_rejected(self):
        def f(p): p['submission']['muse_request_ts']=['x']; p['submission']['muse_explicit_clearance_observed']=True; p['submission']['muse_clearance_ts']='y'
        self.truth_bad(f)
    def test_fake_provider_send_rejected(self): self.truth_bad(lambda p:p['submission'].__setitem__('provider_send_performed',True))
    def test_receipt_escalation(self): self.truth_bad(lambda p:p['commercial_truth'].__setitem__('submission_receipt_confirmed',True))
    def test_acceptance_escalation(self): self.truth_bad(lambda p:p['commercial_truth'].__setitem__('accepted_offer',True))
    def test_payment_escalation(self): self.truth_bad(lambda p:p['commercial_truth'].__setitem__('payment',True))
    def test_revenue_truth_escalation(self): self.truth_bad(lambda p:p['commercial_truth'].__setitem__('revenue',True))
    def test_public_source_guard_rejects_commons_repo_url(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/mod.PROPOSAL_SOURCE).write_text('Public work sample: https://github.com/woahwhattheheck/commons',encoding='utf-8')
            with self.assertRaisesRegex(mod.PacketError,'forbidden public Commons backlink'): mod.validate_public_surface(root)
    def test_public_source_guard_rejects_pages_url_casefolded(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/mod.PROPOSAL_SOURCE).write_text('HTTPS://WOAHWHATTHEHECK.GITHUB.IO/COMMONS/demo',encoding='utf-8')
            with self.assertRaisesRegex(mod.PacketError,'forbidden public Commons backlink'): mod.validate_public_surface(root)
    def test_public_source_guard_accepts_self_contained_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/mod.PROPOSAL_SOURCE).write_text('Standalone proposal; external materials only on request.',encoding='utf-8')
            self.assertEqual(mod.validate_public_surface(root),['NO_PUBLIC_COMMONS_BACKLINK'])
if __name__=='__main__': unittest.main()
