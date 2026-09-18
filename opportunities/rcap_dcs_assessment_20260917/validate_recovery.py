#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
from typing import Any

OP="RCAP-DCS-ASSESSMENT-DIRECT-BID-ZNP-20260917"
BUYER="Rural Community Assistance Partnership (RCAP)"
TITLE="CRM System Assessment and Strategic Planning Services"
RFP_URL="https://www.rcap.org/careers/rfp-assessment-strategic-planning-services/"
ROUTE="gtodd@rcap.org"
ROUTE_DATE="2026-09-17"
DUE="2026-10-04"
BASE_MINOR=2_450_000
OPTIONAL_MINOR=750_000
PDF="Token_Junkie_Labs_RCAP_DCS_Assessment_Proposal_2026-09-17.pdf"
PDF_SHA="5ac9ec259979476fdfac66929f51ba9febc8c87a36e2fe069231646ac4bfc2c6"
PDF_INELIGIBLE_REASON="PRE_POLICY_PDF_CONTAINS_FORBIDDEN_COMMONS_BACKLINK"
STATE="ROUTE_RESOLVED_SOURCE_READY_PDF_REGEN_REQUIRED_NOT_SUBMITTED"
PROPOSAL_SOURCE="PROPOSAL_SOURCE_20260917.md"
FORBIDDEN_COMMONS=(
    "github.com/woahwhattheheck/commons",
    "woahwhattheheck.github.io/commons",
    "raw.githubusercontent.com/woahwhattheheck/commons",
    "api.github.com/repos/woahwhattheheck/commons",
    "codeload.github.com/woahwhattheheck/commons",
    "git@github.com:woahwhattheheck/commons",
)

PUBLIC_TOP_KEYS=frozenset({
    "schema_version","operation_id","buyer","title","observed_at_utc","first_party_rfp_url",
    "public_time_gates","public_scale","public_scope","proposal_requirements",
    "evaluation_weights_percent","hard_conditions","submission","authority","strongest_state",
})
PUBLIC_TIME_KEYS=frozenset({"released","questions_due","responses_to_questions_expected","proposal_due","interviews_if_needed"})
PUBLIC_SCALE_KEYS=frozenset({"active_dcs_users_low","active_dcs_users_high","regional_nonprofits"})
PUBLIC_WEIGHT_KEYS=frozenset({"relevant_assessment_experience","approach","nonprofit_or_similar_experience","qualifications_and_delivery","cost_and_value"})
PUBLIC_HARD_KEYS=frozenset({"respondent_primary_place_of_business_in_us","professional_indemnity_or_liability_coi_required_at_award","mutually_acceptable_executed_agreement_or_sow_required"})
PUBLIC_SUBMISSION_KEYS=frozenset({"format","named_contact","exact_email_resolved","exact_email","route_source_url","route_observed_on","route_must_not_be_guessed"})
PUBLIC_AUTHORITY_KEYS=frozenset({
    "buyer_contact_authorized","proposal_submitted","submission_receipt_confirmed","shortlisted_or_interviewed",
    "selected","agreement_or_sow_executed","coi_sufficiency_confirmed","accepted_offer","award","payment",
    "receivable","booked_revenue","recognized_revenue",
})
TRUTH_TOP_KEYS=frozenset({
    "schema_version","operation_id","proposal_state","buyer","base_offer","discovery","schedule",
    "base_deliverables","base_exclusions","optional_service","artifacts","experience_truth","submission","commercial_truth",
})
TRUTH_BASE_OFFER_KEYS=frozenset({"amount_minor","currency","display","remote_delivery","travel_included","direct_expenses_anticipated","taxes_included","offer_state"})
TRUTH_DISCOVERY_KEYS=frozenset({"stakeholder_sessions","stakeholder_session_minutes","kickoff_included","final_presentation_minutes","consolidated_written_clarification_cycles"})
TRUTH_SCHEDULE_KEYS=frozenset({"estimated_weeks","starts_after","stakeholder_availability_assumption_business_days"})
TRUTH_OPTIONAL_KEYS=frozenset({"name","amount_minor","currency","display","included_in_base","accepted","contents"})
TRUTH_ARTIFACT_KEYS=frozenset({
    "pdf_filename","pdf_sha256","pdf_pages","pdf_visual_verification","pdf_published_in_repo",
    "submission_eligible","regeneration_required","ineligibility_reason","docx_filename","docx_sha256","docx_published_in_repo",
})
TRUTH_EXPERIENCE_KEYS=frozenset({"client_references_invented","authorized_client_references_included","public_work_sample","external_work_sample_included","public_commons_backlink_present"})
TRUTH_SUBMISSION_KEYS=frozenset({
    "exact_recipient_resolved","exact_recipient","route_source_url","route_observed_on","muse_request_ts",
    "muse_explicit_clearance_observed","muse_clearance_ts","provider_send_performed","provider_message_id",
    "provider_thread_id","provider_sent_at","hard_dnr",
})
TRUTH_COMMERCIAL_KEYS=frozenset({
    "proposal_submitted","submission_receipt_confirmed","shortlisted_or_interviewed","selected",
    "agreement_or_sow_executed","coi_sufficiency_confirmed","accepted_offer","award","payment","receivable","revenue",
})

class PacketError(ValueError): pass

def no_dupes(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise PacketError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def load_json(path:Path)->dict[str,Any]:
    try: x=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=no_dupes)
    except PacketError: raise
    except Exception as e: raise PacketError(f"{path.name}: invalid JSON: {e}") from e
    if type(x) is not dict: raise PacketError(f"{path.name}: top level must be object")
    return x

def exact(o:dict[str,Any],k:str,t:type):
    if k not in o: raise PacketError(f"missing key: {k}")
    v=o[k]
    if type(v) is not t: raise PacketError(f"{k}: expected exact {t.__name__}")
    return v

def exact_keys(o:dict[str,Any], allowed:frozenset[str], label:str):
    if type(o) is not dict: raise PacketError(f"{label}: expected object")
    extra=set(o)-allowed
    missing=allowed-set(o)
    if extra or missing:
        raise PacketError(f"{label}: exact key set required extra={sorted(extra)} missing={sorted(missing)}")
    return o

def obj(o,k): return exact(o,k,dict)
def arr(o,k): return exact(o,k,list)

def strings(xs, minimum, label):
    if len(xs)<minimum or any(type(x) is not str or not x.strip() for x in xs): raise PacketError(f"{label}: incomplete")

def validate_public_surface(base:Path):
    path=base/PROPOSAL_SOURCE
    try:
        if path.is_symlink(): raise PacketError("proposal source must not be symlink")
        raw=path.read_bytes()
    except PacketError: raise
    except Exception as e: raise PacketError(f"proposal source unreadable: {e}") from e
    if len(raw)>256_000: raise PacketError("proposal source too large")
    try: text=raw.decode("utf-8")
    except UnicodeError as e: raise PacketError("proposal source must be UTF-8") from e
    folded=text.casefold()
    for forbidden in FORBIDDEN_COMMONS:
        if forbidden in folded:
            raise PacketError(f"proposal source contains forbidden public Commons backlink: {forbidden}")
    return ["NO_PUBLIC_COMMONS_BACKLINK"]

def validate_public(p):
    exact_keys(p, PUBLIC_TOP_KEYS, "public")
    if exact(p,'schema_version',int)!=2: raise PacketError('public: schema')
    for k,w in {'operation_id':OP,'buyer':BUYER,'title':TITLE,'first_party_rfp_url':RFP_URL}.items():
        if exact(p,k,str)!=w: raise PacketError(f'public: drift {k}')
    exact(p,'observed_at_utc',str)
    g=exact_keys(obj(p,'public_time_gates'), PUBLIC_TIME_KEYS, "public.public_time_gates")
    expected={'released':'2026-09-04','questions_due':'2026-09-13','responses_to_questions_expected':'2026-09-18','proposal_due':DUE,'interviews_if_needed':'2026-10-09'}
    for k,w in expected.items():
        if exact(g,k,str)!=w: raise PacketError(f'public: gate drift {k}')
    scale=exact_keys(obj(p,'public_scale'), PUBLIC_SCALE_KEYS, "public.public_scale")
    if exact(scale,'active_dcs_users_low',int)!=400 or exact(scale,'active_dcs_users_high',int)!=500 or exact(scale,'regional_nonprofits',int)!=6: raise PacketError('public: scale drift')
    strings(arr(p,'public_scope'),12,'public scope'); strings(arr(p,'proposal_requirements'),9,'proposal requirements')
    weights=exact_keys(obj(p,'evaluation_weights_percent'), PUBLIC_WEIGHT_KEYS, "public.evaluation_weights_percent")
    expected_weights={'relevant_assessment_experience':30,'approach':25,'nonprofit_or_similar_experience':20,'qualifications_and_delivery':15,'cost_and_value':10}
    for k,w in expected_weights.items():
        if exact(weights,k,int)!=w: raise PacketError(f'public: weight drift {k}')
    if sum(weights.values())!=100: raise PacketError('public: weights do not sum to 100')
    hc=exact_keys(obj(p,'hard_conditions'), PUBLIC_HARD_KEYS, "public.hard_conditions")
    for k in ('respondent_primary_place_of_business_in_us','professional_indemnity_or_liability_coi_required_at_award','mutually_acceptable_executed_agreement_or_sow_required'):
        if exact(hc,k,bool) is not True: raise PacketError(f'public: hard condition weakened {k}')
    s=exact_keys(obj(p,'submission'), PUBLIC_SUBMISSION_KEYS, "public.submission")
    if exact(s,'format',str)!='PDF by email' or exact(s,'named_contact',str)!='Griffin Todd, Data & IT Manager': raise PacketError('public: submission identity drift')
    if exact(s,'exact_email_resolved',bool) is not True or exact(s,'exact_email',str)!=ROUTE: raise PacketError('public: exact route drift')
    if exact(s,'route_source_url',str)!=RFP_URL or exact(s,'route_observed_on',str)!=ROUTE_DATE or exact(s,'route_must_not_be_guessed',bool) is not True: raise PacketError('public: route provenance drift')
    a=exact_keys(obj(p,'authority'), PUBLIC_AUTHORITY_KEYS, "public.authority")
    for k in ('buyer_contact_authorized','proposal_submitted','submission_receipt_confirmed','shortlisted_or_interviewed','selected','agreement_or_sow_executed','coi_sufficiency_confirmed','accepted_offer','award','payment','receivable','booked_revenue','recognized_revenue'):
        if exact(a,k,bool) is not False: raise PacketError(f'public: authority escalation {k}')
    if exact(p,'strongest_state',str)!=STATE: raise PacketError('public: state drift')
    return ['RCAP_IDENTITY_BOUND','OCT04_DUE_BOUND','US_AND_COI_CONDITIONS_BOUND','EXACT_ROUTE_FIRST_PARTY_RESOLVED',STATE]

def validate_truth(p, base:Path):
    exact_keys(p, TRUTH_TOP_KEYS, "truth")
    if exact(p,'schema_version',int)!=2 or exact(p,'operation_id',str)!=OP or exact(p,'buyer',str)!=BUYER: raise PacketError('truth: identity')
    if exact(p,'proposal_state',str)!='PROPOSED_NOT_SUBMITTED_NOT_ACCEPTED': raise PacketError('truth: state')
    b=exact_keys(obj(p,'base_offer'), TRUTH_BASE_OFFER_KEYS, "truth.base_offer")
    if exact(b,'amount_minor',int)!=BASE_MINOR or exact(b,'currency',str)!='USD' or exact(b,'display',str)!='$24,500 fixed': raise PacketError('truth: base price')
    if exact(b,'remote_delivery',bool) is not True or exact(b,'travel_included',bool) is not False or exact(b,'direct_expenses_anticipated',bool) is not False or exact(b,'taxes_included',bool) is not False: raise PacketError('truth: base terms')
    if exact(b,'offer_state',str)!='PROPOSED_NOT_ACCEPTED': raise PacketError('truth: false acceptance')
    d=exact_keys(obj(p,'discovery'), TRUTH_DISCOVERY_KEYS, "truth.discovery")
    if exact(d,'stakeholder_sessions',int)!=6 or exact(d,'stakeholder_session_minutes',int)!=60 or exact(d,'kickoff_included',bool) is not True or exact(d,'final_presentation_minutes',int)!=60 or exact(d,'consolidated_written_clarification_cycles',int)!=1: raise PacketError('truth: discovery drift')
    sched=exact_keys(obj(p,'schedule'), TRUTH_SCHEDULE_KEYS, "truth.schedule")
    if exact(sched,'estimated_weeks',int)!=4 or exact(sched,'stakeholder_availability_assumption_business_days',int)!=10: raise PacketError('truth: schedule drift')
    exact(sched,'starts_after',str)
    strings(arr(p,'base_deliverables'),6,'base deliverables'); strings(arr(p,'base_exclusions'),7,'base exclusions')
    opt=exact_keys(obj(p,'optional_service'), TRUTH_OPTIONAL_KEYS, "truth.optional_service")
    if exact(opt,'amount_minor',int)!=OPTIONAL_MINOR or exact(opt,'display',str)!='$7,500 fixed' or exact(opt,'included_in_base',bool) is not False or exact(opt,'accepted',bool) is not False: raise PacketError('truth: optional/base boundary')
    exact(opt,'name',str); exact(opt,'currency',str)
    strings(arr(opt,'contents'),5,'optional contents')
    art=exact_keys(obj(p,'artifacts'), TRUTH_ARTIFACT_KEYS, "truth.artifacts")
    if exact(art,'pdf_filename',str)!=PDF or exact(art,'pdf_sha256',str)!=PDF_SHA or exact(art,'pdf_pages',int)!=6 or exact(art,'pdf_visual_verification',str)!='PASS_RENDERED_ALL_6_PAGES' or exact(art,'pdf_published_in_repo',bool) is not False: raise PacketError('truth: historical pdf metadata drift')
    if exact(art,'submission_eligible',bool) is not False or exact(art,'regeneration_required',bool) is not True or exact(art,'ineligibility_reason',str)!=PDF_INELIGIBLE_REASON: raise PacketError('truth: stale PDF incorrectly eligible')
    exact(art,'docx_filename',str); exact(art,'docx_sha256',str); exact(art,'docx_published_in_repo',bool)
    exp=exact_keys(obj(p,'experience_truth'), TRUTH_EXPERIENCE_KEYS, "truth.experience_truth")
    if exact(exp,'client_references_invented',bool) is not False or exact(exp,'authorized_client_references_included',bool) is not False: raise PacketError('truth: invented reference claim')
    if exp.get('public_work_sample') is not None or exact(exp,'external_work_sample_included',bool) is not False or exact(exp,'public_commons_backlink_present',bool) is not False: raise PacketError('truth: public work-sample/backlink drift')
    sub=exact_keys(obj(p,'submission'), TRUTH_SUBMISSION_KEYS, "truth.submission")
    if exact(sub,'exact_recipient_resolved',bool) is not True or exact(sub,'exact_recipient',str)!=ROUTE: raise PacketError('truth: exact route drift')
    if exact(sub,'route_source_url',str)!=RFP_URL or exact(sub,'route_observed_on',str)!=ROUTE_DATE: raise PacketError('truth: route provenance drift')
    if arr(sub,'muse_request_ts') or exact(sub,'muse_explicit_clearance_observed',bool) is not False or sub.get('muse_clearance_ts') is not None: raise PacketError('truth: unsupported Muse state')
    if exact(sub,'provider_send_performed',bool) is not False or sub.get('provider_message_id') is not None or sub.get('provider_thread_id') is not None or sub.get('provider_sent_at') is not None or exact(sub,'hard_dnr',bool) is not False: raise PacketError('truth: unsupported send state')
    c=exact_keys(obj(p,'commercial_truth'), TRUTH_COMMERCIAL_KEYS, "truth.commercial_truth")
    for k in ('proposal_submitted','submission_receipt_confirmed','shortlisted_or_interviewed','selected','agreement_or_sow_executed','coi_sufficiency_confirmed','accepted_offer','award','payment','receivable','revenue'):
        if exact(c,k,bool) is not False: raise PacketError(f'truth: commercial escalation {k}')
    return ['USD_24500_BASE_BOUND','SIX_DISCOVERY_SESSIONS_BOUND','FOUR_WEEK_SCHEDULE_BOUND','USD_7500_OPTION_EXCLUDED_BOUND','HISTORICAL_PDF_INELIGIBLE_REGEN_REQUIRED','EXACT_ROUTE_BOUND','NO_SEND_NO_REVENUE_BOUND']

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--public',default='public_opportunity_20260917.json'); ap.add_argument('--truth',default='proposal_truth_20260917.json'); a=ap.parse_args(argv); base=Path(a.public).resolve().parent
    try: checks=validate_public(load_json(Path(a.public)))+validate_truth(load_json(Path(a.truth)),base)+validate_public_surface(base)
    except PacketError as e: print(json.dumps({'valid':False,'error':str(e)},sort_keys=True)); return 2
    print(json.dumps({'valid':True,'buyer_contact_authorized':False,'proposal_submitted':False,'exact_recipient_resolved':True,'exact_recipient':ROUTE,'submission_artifact_ready':False,'accepted_offer':False,'payment':False,'revenue':False,'checks':checks},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
