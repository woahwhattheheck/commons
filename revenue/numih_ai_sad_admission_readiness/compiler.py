"""Evidence-readiness compiler for NUMIH AI SAD 2025-0154-00-00-MPF."""
from __future__ import annotations
import hashlib, json

SCHEMA="numih-ai-sad-admission-readiness/v1"
RESULT_SCHEMA="numih-ai-sad-admission-readiness-result/v1"
RECEIPT_SCHEMA="numih-ai-sad-admission-readiness-receipt/v1"
CATS={1:"AI tools for administrative functions",2:"AI tools for development and hosting",3:"Cross-cutting AI tools",4:"AI technology foundation"}
DIMS=(("legal_aptitude_compliance",20,("legal_registration","binding_authority","exclusion_labor_compliance","gdpr_data_location","professional_liability_insurance")),("recent_ai_references",30,("recent_ai_reference",)),("security_ethics_ai_compliance",30,("security_questionnaire","ssi_charter","confidentiality_commitment","ai_ethics_compliance")),("economic_financial_capacity",20,("global_turnover","ai_domain_turnover_or_substitute")))
APPLICANT_ONLY={"legal_registration","binding_authority","exclusion_labor_compliance"}
STATUSES={"EVIDENCED","CLAIMED_UNVERIFIED","MISSING"}; TRANSLATIONS={"ORIGINAL_FR","CERTIFIED_TRANSLATION","WORKING_TRANSLATION","UNTRANSLATED"}

class ValidationError(ValueError): pass

def _constant(v): raise ValidationError(f"non-finite JSON constant forbidden: {v}")
def _pairs(ps):
    d={}
    for k,v in ps:
        if k in d: raise ValidationError(f"duplicate JSON key: {k}")
        d[k]=v
    return d
def loads_strict(s): return json.loads(s,object_pairs_hook=_pairs,parse_constant=_constant)
def canonical_json(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def digest_json(v): return hashlib.sha256(canonical_json(v).encode()).hexdigest()
def _obj(v,p):
    if type(v) is not dict: raise ValidationError(f"{p} must be an object")
    return v
def _arr(v,p):
    if type(v) is not list: raise ValidationError(f"{p} must be an array")
    return v
def _str(v,p,empty=False):
    if type(v) is not str: raise ValidationError(f"{p} must be a string")
    if not empty and not v.strip(): raise ValidationError(f"{p} must not be empty")
    if len(v)>4096: raise ValidationError(f"{p} too long")
    return v
def _only(o,a,p):
    x=set(o)-set(a)
    if x: raise ValidationError(f"{p} has unknown fields: {sorted(x)}")
def _sha(v,p):
    s=_str(v,p).lower()
    if len(s)!=64 or any(c not in "0123456789abcdef" for c in s): raise ValidationError(f"{p} must be SHA-256 hex")
    return s

def _party(raw,p,role):
    o=_obj(raw,p); allowed={"id","display_name"}|({"commitment_evidence_id"} if role=="PARTNER" else set()); _only(o,allowed,p)
    c=o.get("commitment_evidence_id"); c=_str(c,p+".commitment_evidence_id") if c is not None else None
    return {"id":_str(o.get("id"),p+".id"),"display_name":_str(o.get("display_name"),p+".display_name"),"role":role,"commitment_evidence_id":c}

def _evidence(raw,p):
    o=_obj(raw,p); _only(o,{"id","party_id","kind","status","source","language","translation_status","note"},p)
    st=_str(o.get("status"),p+".status"); tr=_str(o.get("translation_status","UNTRANSLATED"),p+".translation_status")
    if st not in STATUSES: raise ValidationError(f"{p}.status unsupported")
    if tr not in TRANSLATIONS: raise ValidationError(f"{p}.translation_status unsupported")
    src=o.get("source"); parsed=None
    if st=="EVIDENCED":
        src=_obj(src,p+".source"); _only(src,{"locator","sha256","generation"},p+".source")
        parsed={"locator":_str(src.get("locator"),p+".source.locator"),"sha256":_sha(src.get("sha256"),p+".source.sha256"),"generation":_str(src.get("generation"),p+".source.generation")}
    elif src is not None: raise ValidationError(f"{p}.source allowed only when status=EVIDENCED")
    return {"id":_str(o.get("id"),p+".id"),"party_id":_str(o.get("party_id"),p+".party_id"),"kind":_str(o.get("kind"),p+".kind"),"status":st,"source":parsed,"language":_str(o.get("language","und"),p+".language"),"translation_status":tr,"note":_str(o.get("note",""),p+".note",True)}

def validate_packet(packet):
    o=_obj(packet,"$"); _only(o,{"schema","applicant","partners","categories","evidence","dce"},"$")
    if o.get("schema")!=SCHEMA: raise ValidationError(f"$.schema must be {SCHEMA}")
    a=_party(o.get("applicant"),"$.applicant","APPLICANT"); ps=[_party(v,f"$.partners[{i}]","PARTNER") for i,v in enumerate(_arr(o.get("partners",[]),"$.partners"))]
    if len(ps)>15: raise ValidationError("too many partners")
    ids=[a["id"]]+[p["id"] for p in ps]
    if len(ids)!=len(set(ids)): raise ValidationError("duplicate party id")
    cs=[]
    for i,v in enumerate(_arr(o.get("categories"),"$.categories")):
        if type(v) is not int: raise ValidationError(f"$.categories[{i}] must be an integer")
        cs.append(v)
    if not cs or len(cs)>4: raise ValidationError("$.categories must contain 1..4 entries")
    if len(cs)!=len(set(cs)): raise ValidationError("duplicate category")
    if any(c not in CATS for c in cs): raise ValidationError("categories must be integers 1..4")
    es=[_evidence(v,f"$.evidence[{i}]") for i,v in enumerate(_arr(o.get("evidence"),"$.evidence"))]
    if len(es)>512: raise ValidationError("too many evidence rows")
    eids=[e["id"] for e in es]
    if len(eids)!=len(set(eids)): raise ValidationError("duplicate evidence id")
    known=set(ids)
    for e in es:
        if e["party_id"] not in known: raise ValidationError(f"unknown evidence party: {e['party_id']}")
        if e["kind"] in APPLICANT_ONLY and e["party_id"]!=a["id"]: raise ValidationError(f"{e['kind']} must belong to applicant")
    em={e["id"]:e for e in es}
    for p in ps:
        c=p["commitment_evidence_id"]
        if c:
            e=em.get(c)
            if not e or e["party_id"]!=p["id"] or e["kind"]!="partner_capacity_commitment": raise ValidationError(f"partner {p['id']} commitment evidence is cross-party or wrong kind")
    d=_obj(o.get("dce"),"$.dce"); _only(d,{"document_id","sha256","generation","source_locator"},"$.dce")
    d={"document_id":_str(d.get("document_id"),"$.dce.document_id"),"sha256":_sha(d.get("sha256"),"$.dce.sha256"),"generation":_str(d.get("generation"),"$.dce.generation"),"source_locator":_str(d.get("source_locator"),"$.dce.source_locator")}
    return a,ps,sorted(cs),es,d

def _committed(p,em):
    e=em.get(p["commitment_evidence_id"]) if p["commitment_evidence_id"] else None
    return bool(e and e["status"]=="EVIDENCED")
def _effective(kind,aid,pm,es,em):
    out=[]
    for e in es:
        if e["kind"]!=kind or e["status"]!="EVIDENCED": continue
        if e["party_id"]==aid: out.append(e)
        elif kind not in APPLICANT_ONLY and (p:=pm.get(e["party_id"])) and _committed(p,em): out.append(e)
    return sorted(out,key=lambda e:(e["party_id"],e["id"]))
def _coverage(kind,aid,pm,es,em):
    ok=_effective(kind,aid,pm,es,em)
    if ok:
        e=ok[0]; return {"requirement":kind,"coverage":"EVIDENCED","party_id":e["party_id"],"evidence_id":e["id"],"source_generation":e["source"]["generation"]}
    rows=sorted((e for e in es if e["kind"]==kind),key=lambda e:(e["party_id"],e["id"]))
    for e in rows:
        if e["status"]=="CLAIMED_UNVERIFIED": return {"requirement":kind,"coverage":"CLAIMED_UNVERIFIED","party_id":e["party_id"],"evidence_id":e["id"],"source_generation":None}
    for e in rows:
        p=pm.get(e["party_id"])
        if e["status"]=="EVIDENCED" and p and not _committed(p,em): return {"requirement":kind,"coverage":"PARTNER_COMMITMENT_MISSING","party_id":e["party_id"],"evidence_id":e["id"],"source_generation":e["source"]["generation"]}
    return {"requirement":kind,"coverage":"MISSING","party_id":None,"evidence_id":None,"source_generation":None}

def compile_packet(packet):
    a,ps,cs,es,dce=validate_packet(packet); pm={p["id"]:p for p in ps}; em={e["id"]:e for e in es}; dims=[]; total=0.0; core=True
    for name,w,reqs in DIMS:
        rows=[_coverage(k,a["id"],pm,es,em) for k in reqs]; n=sum(r["coverage"]=="EVIDENCED" for r in rows); pts=w*n/len(rows); total+=pts; core=core and n==len(rows)
        dims.append({"dimension":name,"published_weight":w,"requirements_total":len(rows),"requirements_evidenced":n,"evidence_coverage_points":round(pts,6),"rows":rows})
    cat=[]; cats_ok=True
    for c in cs:
        rows=_effective(f"category_fit_{c}",a["id"],pm,es,em)
        if rows:
            e=rows[0]; cat.append({"category":c,"name":CATS[c],"state":"EVIDENCED","party_id":e["party_id"],"evidence_id":e["id"]})
        else: cats_ok=False; cat.append({"category":c,"name":CATS[c],"state":"HOLD","party_id":None,"evidence_id":None})
    q=sorted(({"evidence_id":e["id"],"party_id":e["party_id"],"language":e["language"],"translation_status":e["translation_status"],"action":"OWNER_REVIEW_FRENCH_TRANSLATION_AND_CERTIFICATION_REQUIREMENT"} for e in es if e["status"]=="EVIDENCED" and e["language"].lower()!="fr" and e["translation_status"] not in {"ORIGINAL_FR","CERTIFIED_TRANSLATION"}),key=lambda x:(x["party_id"],x["evidence_id"]))
    result={"schema":RESULT_SCHEMA,"operation":"2025-0154-00-00-MPF","applicant":{"party_id":a["id"],"display_name":a["display_name"]},"partners":[{"party_id":p["id"],"display_name":p["display_name"],"commitment_evidence_id":p["commitment_evidence_id"],"capacity_composable":_committed(p,em)} for p in sorted(ps,key=lambda p:p["id"])],"categories":cat,"rubric":{"label":"PUBLISHED_RUBRIC_EVIDENCE_COVERAGE_NOT_SPONSOR_SCORE","published_total_weight":100,"evidence_coverage_points":round(total,6),"dimensions":dims},"translation_queue":q,"dce":{**dce,"currentness":"CURRENTNESS_UNVERIFIED","reason":"Caller metadata cannot establish latest authoritative PLACE document currentness."},"packet_state":"PACKET_REVIEW_READY" if core and cats_ok and not q else "INCOMPLETE_EVIDENCE","external_submission_state":"HOLD_CURRENTNESS_AND_OWNER_ACTIONS","owner_actions":["Name and verify the actual applicant legal entity and national registration mapping.","Refresh the authoritative PLACE DCE immediately before admission work.","Confirm current foreign-bidder filing, certificate, and French translation requirements.","Resolve every translation/certification queue item and verify partner commitments/capacity.","Complete and verify current DUME, security questionnaire, SSI/confidentiality materials.","Review pricing, declarations, e-signature and deposit in the provider surface; this compiler performs none."],"authority":{"buyer_contact":False,"provider_login_or_account":False,"dume_certification":False,"legal_declaration":False,"electronic_signature":False,"pricing_commitment":False,"submission_or_deposit":False,"admission":False,"contract_award":False,"payment":False,"recognized_revenue":False},"disclaimer":"Evidence-readiness compiler only. Coverage points mirror published rubric weights for packet completeness; they are not a sponsor score, eligibility/admission prediction, legal opinion, award or revenue claim."}
    return {**result,"receipt":{"schema":RECEIPT_SCHEMA,"input_sha256":digest_json(packet),"result_sha256":digest_json(result)}}
def verify_result(packet,result):
    if type(result) is not dict or type(result.get("receipt")) is not dict: return False
    r=result["receipt"]; semantic=dict(result); semantic.pop("receipt",None)
    return r.get("schema")==RECEIPT_SCHEMA and r.get("input_sha256")==digest_json(packet) and r.get("result_sha256")==digest_json(semantic) and compile_packet(packet)==result
def render_markdown(r):
    lines=["# NUMIH AI SAD admission-readiness packet","",f"- Packet state: **{r['packet_state']}**",f"- External submission state: **{r['external_submission_state']}**",f"- DCE currentness: **{r['dce']['currentness']}**",f"- Published-rubric evidence coverage: **{r['rubric']['evidence_coverage_points']}/100** (not a sponsor score)","","## Categories",""]
    for x in r["categories"]:
        suffix=f" via `{x['party_id']}` / `{x['evidence_id']}`" if x["evidence_id"] else ""; lines.append(f"- {x['category']} — {x['name']}: **{x['state']}**{suffix}")
    lines += ["","## Translation/certification queue",""] + ([f"- `{x['evidence_id']}` ({x['language']}, {x['translation_status']}): {x['action']}" for x in r["translation_queue"]] or ["- No unresolved queue item in supplied evidence."])
    lines += ["","## Owner actions",""]+[f"- {x}" for x in r["owner_actions"]]+["","## Authority ceiling","","All external mutation/award/payment/revenue authority fields are `false`.","",r["disclaimer"],""]
    return "\n".join(lines)
