from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

UTC=timezone.utc
DEADLINE=datetime(2026,9,18,13,0,tzinfo=UTC)
QUESTIONS_DEADLINE=datetime(2026,9,14,15,0,tzinfo=UTC)
HEX=re.compile(r'^[0-9a-f]{64}$')
REQUIRED_SOURCES=('concept_template','general_solicitation','innovation_call')
SECTIONS=(
 ('1','Problem Understanding'),('2','Proposed Concept & Vision'),
 ('3','High-Level Technical Approach'),('4','Intellectual Property & Data Rights'),
 ('5','Risk & Opportunity Spotlight'),('6','Rough Order of Magnitude (ROM)'))
ARCH=(
 'unified_mission_shell','identity_provider_adapter_plane','attribute_policy_decision_layer',
 'workflow_context_broker','api_event_integration_plane','legacy_continuity_sidecars_and_canaries',
 'observability_issue_and_release_ledger','iac_devsecops_delivery_plane','continuous_ato_evidence_fabric')
PHASES=(
 (1,'Discovery/UX/baseline+sustainment transition',('persona_role_attribute_matrix','ie_interface_inventory','sustainment_transition_receipt','test_backlog')),
 (2,'Core unified-access prototype',('multi_idp_mfa_demo','attribute_policy_tests','dashboard_accessibility','workflow_continuity','legacy_canaries')),
 (3,'IE onboarding/workflow validation',('eapp_iep_pvq_pdt_access_tests','handoff_contract_tests','context_continuity','reusable_onboarding_contract')),
 (4,'Validation/ATO/production readiness',('gat_uat_regression_integration','performance_reliability_accessibility_security','ato_evidence_ledger','issue_disposition','production_rom')))
QUESTIONS=(
 'Can a cleared lead performer use an uncleared/non-FCL subcontractor strictly for unclassified architecture, test-harness, and evidence-engineering work outside Government/CUI/classified environments?',
 'What transition artifacts and incumbent assistance will DCSA furnish for the IE sustainment assumption within the first 30 days?',
 'Which identity-provider, role/attribute, MuleSoft/API, and event-interface contracts will be available during Phase 1, and is an unclassified contract-test simulator acceptable before CAC/GFE access?',
 'How should significant nontraditional-defense-contractor participation under 10 U.S.C. 4022 be evidenced in the concept paper?',
 'Will DCSA accept a parametric per-application onboarding/sustainment ROM model for later applications not yet selected?')


def dt(s):
 x=datetime.fromisoformat(s.replace('Z','+00:00'))
 if x.tzinfo is None: raise ValueError('timezone-aware timestamp required')
 return x.astimezone(UTC)

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(x): return hashlib.sha256(canon(x)).hexdigest()
def h(x): return isinstance(x,str) and bool(HEX.fullmatch(x))

def source_gate(rows):
 by={}; p=[]
 for r in rows if isinstance(rows,list) else []:
  k=r.get('key') if isinstance(r,dict) else None
  if not isinstance(k,str) or not k: p.append('SOURCE_KEY_INVALID'); continue
  if k in by: p.append('SOURCE_DUPLICATE:'+k); continue
  by[k]=r
 for k in REQUIRED_SOURCES:
  r=by.get(k)
  if not r: p.append('SOURCE_MISSING:'+k); continue
  if r.get('authority')!='FIRST_PARTY_RETAINED': p.append('SOURCE_NOT_RETAINED_FIRST_PARTY:'+k)
  if not h(r.get('sha256')): p.append('SOURCE_HASH_INVALID:'+k)
  if not str(r.get('generation','')).strip(): p.append('SOURCE_GENERATION_INVALID:'+k)
 return not p,p

def eligibility_gate(c,now):
 e=c.get('eligibility',{}); f=e.get('facility_clearance',{}); s=e.get('assigned_personnel',{}); o=e.get('ota_eligibility',{}); p=[]
 if f.get('level')!='TOP_SECRET': p.append('FCL_TOP_SECRET_NOT_EVIDENCED')
 if f.get('status')!='ACTIVE_VERIFIED': p.append('FCL_ACTIVE_NOT_EVIDENCED')
 if not h(f.get('evidence_sha256')): p.append('FCL_EVIDENCE_HASH_INVALID')
 try:
  if dt(f['valid_through'])<now: p.append('FCL_EXPIRED')
 except Exception: p.append('FCL_VALIDITY_INVALID')
 if s.get('all_us_citizens') is not True: p.append('PERSONNEL_CITIZENSHIP_NOT_EVIDENCED')
 if s.get('all_at_least_interim_secret') is not True: p.append('PERSONNEL_CLEARANCE_NOT_EVIDENCED')
 if not h(s.get('evidence_sha256')): p.append('PERSONNEL_EVIDENCE_HASH_INVALID')
 if o.get('status')!='VERIFIED': p.append('OTA_ELIGIBILITY_NOT_EVIDENCED')
 if o.get('basis') not in ('SIGNIFICANT_NDC','ALL_SIGNIFICANT_SMALL_OR_NDC','ONE_THIRD_COST_SHARE'): p.append('OTA_BASIS_INVALID')
 if not h(o.get('evidence_sha256')): p.append('OTA_EVIDENCE_HASH_INVALID')
 return not p,p

def targets(rows):
 out=[]; p=[]; seen=set()
 for r in rows if isinstance(rows,list) else []:
  org=str(r.get('organization','')).strip() if isinstance(r,dict) else ''
  if not org: p.append('TARGET_ORG_MISSING'); continue
  if org.casefold() in seen: p.append('TARGET_DUPLICATE:'+org); continue
  seen.add(org.casefold()); ev=[]
  for x in r.get('evidence',[]):
   if not isinstance(x,dict) or not str(x.get('url','')).startswith('https://'): p.append('TARGET_EVIDENCE_INVALID:'+org); continue
   ev.append({'claim':str(x.get('claim','')),'url':str(x['url']),'source_class':str(x.get('source_class','PUBLIC_FIRST_PARTY_OR_GOV'))})
  if not ev: p.append('TARGET_EVIDENCE_MISSING:'+org); continue
  out.append({'organization':org,'dcsa_relevance':bool(r.get('dcsa_relevance')),'app_modernization':bool(r.get('app_modernization')),'cleared_workforce_signal':bool(r.get('cleared_workforce_signal')),'fcl':'REVERIFY_NOT_PROVEN','route':'RESEARCH_ONLY_NO_CONTACT_COORDINATES','evidence':ev})
 return sorted(out,key=lambda x:x['organization'].casefold()),p

def pursuit(case,now):
 now=now.astimezone(UTC); so,sp=source_gate(case.get('sources',[])); eo,ep=eligibility_gate(case,now); tt,tp=targets(case.get('teaming_targets',[])); dp=[]
 if now>=DEADLINE: dp.append('CONCEPT_DEADLINE_PASSED')
 status='HOLD' if dp else ('DIRECT_READY' if so and eo else ('TEAMING_REQUIRED' if tt else 'HOLD'))
 x={'schema':'dcsa-innovation-call-01/v2','opportunity':{'id':'DCSAInnovationCall01','parent':'HS0021-26-CSO-DCSA','concept_deadline_utc':'2026-09-18T13:00:00Z','questions_deadline_utc':'2026-09-14T15:00:00Z'},'evaluated_at':now.isoformat().replace('+00:00','Z'),'status':status,'direct_readiness':{'source_authority_ready':so,'eligibility_ready':eo,'problems':sorted(sp+ep+dp)},'architecture':list(ARCH),'acceptance_matrix':[{'phase':n,'name':name,'evidence':list(ev)} for n,name,ev in PHASES],'teaming':{'targets':tt,'target_problems':sorted(tp),'workshare':{'name':'Unified Access Integration + Acceptance Evidence Workshare','scope':['integration_architecture_and_adapter_contracts','legacy_continuity_canaries_and_release_gates','role_attribute_policy_contract_tests','workflow_context_continuity_tests','phase_1_to_4_acceptance_evidence_matrix','continuous_ato_evidence_and_issue_disposition_ledger','production_onboarding_contract_and_rom_model'],'commercial_state':'PRICE_OWNER_APPROVAL_REQUIRED','outbound_authorized':False}},'questions_draft_only':list(QUESTIONS),'authority':{k:False for k in ('send_questions','submit_concept_paper','accept_terms','assert_clearance','contact_prime','spend','sign','claim_award_payment_revenue')}}
 x['receipt_sha256']=digest(x); return x

def concept(case,now):
 p=pursuit(case,now); ci=case.get('concept_inputs',{}); cover=ci.get('cover',{}); probs=list(p['direct_readiness']['problems'])
 required=('lead_organization_name','organization_type','address','city','country','zip','tin_or_ein','uei','cage_code','technical_poc','administrative_poc')
 cv={'innovation_call':'DCSAInnovationCall01','naics':'541512','title':str(cover.get('title') or 'Unified Mission Access Integration and Evidence Fabric')}
 for k in required:
  v=str(cover.get(k,'')).strip(); cv[k]=v or '[OWNER INPUT REQUIRED]'
  if not v: probs.append('OWNER_INPUT_REQUIRED:'+k)
 rom=ci.get('rom',{}); amount=rom.get('total_usd_minor'); rsha=rom.get('basis_sha256'); approved=rom.get('owner_approved') is True
 if not isinstance(amount,int) or isinstance(amount,bool) or amount<=0: probs.append('ROM_OWNER_INPUT_REQUIRED'); amount=None
 if not h(rsha): probs.append('ROM_BASIS_EVIDENCE_REQUIRED'); rsha=None
 if not approved: probs.append('ROM_OWNER_APPROVAL_REQUIRED')
 pp=[]
 for r in ci.get('past_performance',[]) if isinstance(ci.get('past_performance',[]),list) else []:
  if isinstance(r,dict) and str(r.get('reference_id','')).strip() and str(r.get('statement','')).strip() and h(r.get('evidence_sha256')): pp.append({'reference_id':str(r['reference_id']),'statement':str(r['statement']),'evidence_sha256':r['evidence_sha256']})
 if not pp: probs.append('PAST_PERFORMANCE_OWNER_EVIDENCE_REQUIRED')
 tf=ci.get('template_format',{}); tok=h(tf.get('retained_template_sha256')) and tf.get('format_verified') is True
 if not tok: probs.append('GOVERNMENT_TEMPLATE_FORMAT_NOT_VERIFIED')
 if p['status']=='HOLD': state='HOLD'
 elif p['status']=='TEAMING_REQUIRED': state='TEAMING_DRAFT_OWNER_INPUT_REQUIRED'
 elif probs: state='OWNER_INPUT_REQUIRED'
 else: state='CONTENT_READY_FORMAT_VERIFIED_NOT_SUBMITTED'
 sec=[
 {'section':'1','title':SECTIONS[0][1],'content':['DCSA mission users traverse fragmented applications; the target is a unified access layer that preserves continuity while legacy capabilities remain live.','Sustainment transition and operational continuity are treated as acceptance evidence, not assumptions.']},
 {'section':'2','title':SECTIONS[1][1],'content':['Provide one unified mission shell over live services instead of a big-bang replacement.','Use explicit identity, policy, workflow-context, adapter, canary and rollback contracts so applications can modernize independently.']},
 {'section':'3','title':SECTIONS[2][1],'content':['Architecture modules: '+', '.join(ARCH)+'.','Acceptance is phase-bound to executable evidence for identity, workflow continuity, security, accessibility, performance and production transition.']},
 {'section':'4','title':SECTIONS[3][1],'content':['Background IP, foreground IP, third-party dependencies, licenses, and proposed Government rights remain OWNER/LEGAL INPUT REQUIRED. No rights position is inferred.']},
 {'section':'5','title':SECTIONS[4][1],'content':['Primary risk: modernization disrupts live mission workflows if identity/context/release semantics are coupled to a monolithic cutover.','Mitigate with strangler-style onboarding, continuity canaries, contract tests, issue disposition and rollback evidence per generation.']},
 {'section':'6','title':SECTIONS[5][1],'content':['ROM is not invented. Insert only an owner-approved phased estimate supported by a retained estimating basis and OTA/cost-share evidence.']}]
 x={'schema':'dcsa-innovation-call-01-concept/v2','pursuit_status':p['status'],'concept_state':state,'cover':cv,'sections':sec,'past_performance':sorted(pp,key=lambda x:x['reference_id']),'rom':{'total_usd_minor':amount,'basis_sha256':rsha,'owner_approved':approved,'state':'OWNER_APPROVED' if amount and rsha and approved else 'OWNER_INPUT_REQUIRED'},'readiness_problems':sorted(set(probs)),'format_contract':{'sections_1_to_6_page_limit':6,'page_size':'8.5x11','font':'Calibri Light','font_size_pt':11,'margins_in':1,'spacing':'single','retained_template_sha256':tf.get('retained_template_sha256'),'format_verified':tok,'page_compliance_claimed':False},'authority':{k:False for k in ('submit','send','assert_clearance','assert_past_performance','approve_rom','accept_terms','sign','claim_award_payment_revenue')}}
 x['receipt_sha256']=digest(x); return x

def verify(case,packet,now,kind): return canon(concept(case,now) if kind=='concept' else pursuit(case,now))==canon(packet)
def main():
 a=argparse.ArgumentParser(); a.add_argument('case',type=Path); a.add_argument('--now',required=True); a.add_argument('--kind',choices=('pursuit','concept'),default='pursuit'); a.add_argument('--output',type=Path); a.add_argument('--verify',type=Path); z=a.parse_args(); c=json.loads(z.case.read_text()); n=dt(z.now); x=concept(c,n) if z.kind=='concept' else pursuit(c,n)
 if z.verify:
  ok=verify(c,json.loads(z.verify.read_text()),n,z.kind); print('VALID' if ok else 'INVALID'); return 0 if ok else 2
 s=json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n'; z.output.write_text(s) if z.output else print(s,end=''); return 0
if __name__=='__main__': raise SystemExit(main())
