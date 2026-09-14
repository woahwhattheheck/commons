from __future__ import annotations
import copy, json
from .engine import evaluate

AS_OF="2026-09-13T14:30:00Z"

def fixture():
    packet={
      "schema":"commons.ai-ready-roanoke/v1","opportunity_id":"RFP-127519","buyer":"Botetourt County Economic Development Authority",
      "sources":[
        {"source_id":"rfp-public-mirror-20260831","doc_kind":"RFP","generation":"2026-08-31","authority":"BUYER_DOCUMENT_MIRROR","source_ref":"govtribe:ai-ready-roanoke-rfp-final","content_sha256":None,"captured_at":"2026-09-13T14:10:00Z","current":True,"supersedes":None},
        {"source_id":"addendum-1-public-mirror-20260901","doc_kind":"ADDENDUM","generation":"2026-09-01","authority":"BUYER_DOCUMENT_MIRROR","source_ref":"govtribe:rfp-addendum-no-1","content_sha256":None,"captured_at":"2026-09-13T14:11:00Z","current":True,"supersedes":None}
      ],
      "source_set_complete":True,
      "deadlines":{"questions_due":"2026-09-25T23:59:00Z","proposal_due":"2026-10-03T03:59:00Z","deadline_source_id":"addendum-1-public-mirror-20260901"},
      "gates":[],
      "partner":{"candidate_id":"camoin-associates","confirmed":False,"commercial_workshare_agreed":False,"evidence_refs":[]},
      "outreach":{"state":"SENT_NOT_ACCEPTED","provider_receipt_id":"gmail-1a09b2684d2a2040"},
      "budget":{"math_valid":False,"owner_approved":False,"total_cents":0},
      "owner_release":False
    }
    for route in ("PRIME","TEAM"):
      for gid in ("regional_feasibility_experience","primary_employer_research","real_estate_program_cost_modeling","governance_design","in_region_interview_capacity","similar_references","key_personnel","virginia_scc_or_valid_exception","required_insurance","proposal_budget_approved","signature_authority"):
        state="MISSING" if route=="PRIME" else "PARTNER_CURABLE"
        packet["gates"].append({"gate_id":gid,"route":route,"state":state,"evidence_refs":[]})
    return packet

def main()->int:
    p=fixture(); out=evaluate(p,AS_OF)
    assert out["disposition"]=="PARTNER_OUTREACH_READY"
    assert out["outreach"]["state"]=="SENT_NOT_ACCEPTED"
    assert not out["source_posture"]["official_submission_bytes_complete"]
    assert not any(out["authority"].values())
    print(json.dumps({"disposition":out["disposition"],"outreach":out["outreach"],"receipt_sha256":out["receipt_sha256"],"days_to_proposal":out["days_to_proposal"]},sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
