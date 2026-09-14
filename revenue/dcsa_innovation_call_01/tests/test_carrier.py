import copy,json,sys,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from carrier import pursuit,concept,verify
NOW=datetime(2026,9,14,5,0,tzinfo=timezone.utc)
def load(): return json.loads((ROOT/'case.example.json').read_text())
def hh(c): return c*64
def direct(c):
 x=copy.deepcopy(c)
 for i,r in enumerate(x['sources']): r['authority']='FIRST_PARTY_RETAINED'; r['sha256']=hh(chr(97+i))
 x['eligibility']={'facility_clearance':{'level':'TOP_SECRET','status':'ACTIVE_VERIFIED','evidence_sha256':hh('d'),'valid_through':'2027-01-01T00:00:00Z'},'assigned_personnel':{'all_us_citizens':True,'all_at_least_interim_secret':True,'evidence_sha256':hh('e')},'ota_eligibility':{'status':'VERIFIED','basis':'SIGNIFICANT_NDC','evidence_sha256':hh('f')}}; return x
class T(unittest.TestCase):
 def test_example_teaming(self):
  p=pursuit(load(),NOW); self.assertEqual(p['status'],'TEAMING_REQUIRED'); self.assertFalse(p['authority']['contact_prime']); self.assertEqual(p['teaming']['targets'][0]['fcl'],'REVERIFY_NOT_PROVEN')
 def test_direct_requires_retained_sources(self):
  c=direct(load()); self.assertEqual(pursuit(c,NOW)['status'],'DIRECT_READY'); c['sources'][0]['authority']='PUBLIC_MIRROR_NOT_RETAINED'; self.assertEqual(pursuit(c,NOW)['status'],'TEAMING_REQUIRED')
 def test_fcl(self):
  c=direct(load()); c['eligibility']['facility_clearance']['level']='SECRET'; self.assertIn('FCL_TOP_SECRET_NOT_EVIDENCED',pursuit(c,NOW)['direct_readiness']['problems'])
 def test_personnel(self):
  c=direct(load()); c['eligibility']['assigned_personnel']['all_us_citizens']=False; self.assertIn('PERSONNEL_CITIZENSHIP_NOT_EVIDENCED',pursuit(c,NOW)['direct_readiness']['problems'])
 def test_ota(self):
  c=direct(load()); c['eligibility']['ota_eligibility']['status']='NO'; self.assertIn('OTA_ELIGIBILITY_NOT_EVIDENCED',pursuit(c,NOW)['direct_readiness']['problems'])
 def test_deadline(self): self.assertEqual(pursuit(load(),datetime(2026,9,18,13,0,tzinfo=timezone.utc))['status'],'HOLD')
 def test_target_order_deterministic(self):
  a=load(); b=load(); b['teaming_targets'].reverse(); self.assertEqual(pursuit(a,NOW),pursuit(b,NOW))
 def test_target_duplicate(self):
  c=load(); c['teaming_targets'].append(copy.deepcopy(c['teaming_targets'][0])); self.assertIn('TARGET_DUPLICATE:SAIC',pursuit(c,NOW)['teaming']['target_problems'])
 def test_no_contact_coordinates(self):
  s=json.dumps(pursuit(load(),NOW)); self.assertNotIn('@',s); self.assertFalse(pursuit(load(),NOW)['teaming']['workshare']['outbound_authorized'])
 def test_pursuit_tamper(self):
  c=load(); p=pursuit(c,NOW); self.assertTrue(verify(c,p,NOW,'pursuit')); p['status']='DIRECT_READY'; self.assertFalse(verify(c,p,NOW,'pursuit'))
 def test_concept_owner_inputs(self):
  p=concept(load(),NOW); self.assertEqual(p['concept_state'],'TEAMING_DRAFT_OWNER_INPUT_REQUIRED'); self.assertIn('OWNER_INPUT_REQUIRED:lead_organization_name',p['readiness_problems']); self.assertFalse(p['authority']['submit'])
 def test_rom_not_invented(self):
  p=concept(load(),NOW); self.assertEqual(p['rom']['state'],'OWNER_INPUT_REQUIRED'); self.assertIn('ROM_OWNER_APPROVAL_REQUIRED',p['readiness_problems'])
 def test_past_performance_not_invented(self): self.assertIn('PAST_PERFORMANCE_OWNER_EVIDENCE_REQUIRED',concept(load(),NOW)['readiness_problems'])
 def test_template_not_invented(self):
  p=concept(load(),NOW); self.assertIn('GOVERNMENT_TEMPLATE_FORMAT_NOT_VERIFIED',p['readiness_problems']); self.assertFalse(p['format_contract']['page_compliance_claimed']); self.assertEqual(len(p['sections']),6)
 def test_concept_tamper(self):
  c=load(); p=concept(c,NOW); self.assertTrue(verify(c,p,NOW,'concept')); p['sections'][0]['content'][0]='invented'; self.assertFalse(verify(c,p,NOW,'concept'))
 def test_all_authority_false(self):
  for x in (pursuit(load(),NOW),concept(load(),NOW)): self.assertTrue(all(v is False for v in x['authority'].values()))
if __name__=='__main__': unittest.main()
