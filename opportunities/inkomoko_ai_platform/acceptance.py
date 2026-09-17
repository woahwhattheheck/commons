from __future__ import annotations
from .core import CarrierError,digest,keys,text

SCHEMA="inkomoko-synthetic-acceptance/v1"
LANG={"en","fr","rw","sw"};CHANNEL={"WEB","WHATSAPP","STAFF_CONSOLE"}
ROLE={"ENTREPRENEUR","BUSINESS_ADVISOR","SUPPORT_AGENT","ADMIN"}
TYPE={"TRAINING_STAGE","FAQ","LOAN_ENQUIRY","INTEGRATION_CALL","INTEGRATION_RESULT","ESCALATION_REQUEST","HUMAN_HANDOFF","CHANNEL_SWITCH","AUDIT"}
SYSTEM={None,"CBS","INKOBOOK","PBI"}
STAGES=["IDEATION","INVESTMENT_READINESS","BUSINESS_PLANNING","MARKET_ENTRY"]
EVENT={"seq","type","channel","conversation_id","context_sha256","request_id","system","stage","subject_id","result"}

def syn(v,label):
    s=text(v,label,128)
    if not s.startswith("SYN-") or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-" for c in s):raise CarrierError(f"{label} must be a SYN-* synthetic identifier")
    return s
def sha(v,label):
    s=text(v,label,64)
    if len(s)!=64 or any(c not in "0123456789abcdef" for c in s):raise CarrierError(f"{label} must be lowercase SHA-256")
    return s

def evaluate_scenario(s):
    keys(s,{"schema_version","scenario_id","language","initial_channel","role","events"},"scenario")
    if type(s["schema_version"]) is not int or s["schema_version"]!=1:raise CarrierError("unsupported acceptance schema")
    sid=syn(s["scenario_id"],"scenario_id");language=text(s["language"],"language",8);channel=text(s["initial_channel"],"initial_channel",32);role=text(s["role"],"role",32)
    if language not in LANG:raise CarrierError("unsupported test language")
    if channel not in CHANNEL:raise CarrierError("unsupported initial channel")
    if role not in ROLE:raise CarrierError("unsupported role")
    events=s["events"]
    if type(events) is not list or not events or len(events)>500:raise CarrierError("events must be non-empty bounded list")
    findings=[];stages=[];pending=None;requests={};results=set();audits=set();prev=0;conv=None;current=channel
    for i,e in enumerate(events):
        keys(e,EVENT,f"event[{i}]");seq=e["seq"]
        if type(seq) is not int or seq<=prev:raise CarrierError("event seq must be strictly increasing positive integers")
        prev=seq;typ=text(e["type"],"event.type",40);ch=text(e["channel"],"event.channel",32);cid=syn(e["conversation_id"],"conversation_id");ctx=sha(e["context_sha256"],"context_sha256")
        if typ not in TYPE:raise CarrierError(f"unsupported event type: {typ}")
        if ch not in CHANNEL:raise CarrierError("unsupported event channel")
        req=syn(e["request_id"],"request_id") if e["request_id"] is not None else None
        system=e["system"];stage=e["stage"];subject=syn(e["subject_id"],"subject_id") if e["subject_id"] is not None else None;text(e["result"],"result",128)
        if system not in SYSTEM:raise CarrierError("unsupported integration system")
        if stage is not None and stage not in STAGES:raise CarrierError("unsupported training stage")
        if conv is None:conv=cid
        elif cid!=conv:findings.append(("CONVERSATION_CONTEXT_BREAK",f"event {seq} changed conversation_id"))
        if typ=="CHANNEL_SWITCH":
            if ch==current:findings.append(("NOOP_CHANNEL_SWITCH",f"event {seq} did not change channel"))
            current=ch
        elif ch!=current:findings.append(("CHANNEL_WITHOUT_SWITCH",f"event {seq} used {ch} before CHANNEL_SWITCH"))
        if typ=="TRAINING_STAGE":
            if stage is None:findings.append(("STAGE_MISSING",f"event {seq}"))
            else:stages.append(stage)
        if typ=="ESCALATION_REQUEST":
            if pending is not None:findings.append(("OVERLAPPING_ESCALATION",f"event {seq} started a second escalation"))
            pending=(cid,ctx)
        if typ=="HUMAN_HANDOFF":
            if pending is None:findings.append(("UNREQUESTED_HANDOFF",f"event {seq} lacks escalation request"))
            else:
                if (cid,ctx)!=pending:findings.append(("ESCALATION_CONTEXT_LOST",f"event {seq} changed conversation/context evidence"))
                pending=None
        if typ=="LOAN_ENQUIRY" and subject is None:findings.append(("LOAN_SUBJECT_MISSING",f"event {seq} lacks synthetic subject"))
        if typ=="INTEGRATION_CALL":
            if req is None or system is None:findings.append(("INTEGRATION_IDENTITY_MISSING",f"event {seq}"))
            elif req in requests:findings.append(("DUPLICATE_INTEGRATION_REQUEST",req))
            else:requests[req]=system
        if typ=="INTEGRATION_RESULT":
            if req is None or req not in requests:findings.append(("ORPHAN_INTEGRATION_RESULT",req or f"event {seq}"))
            elif req in results:findings.append(("DUPLICATE_INTEGRATION_RESULT",req))
            else:results.add(req)
        if typ=="AUDIT":
            if req is None:findings.append(("AUDIT_TARGET_MISSING",f"event {seq}"))
            else:audits.add(req)
    if pending is not None:findings.append(("ESCALATION_UNRESOLVED","trace ended before HUMAN_HANDOFF"))
    if stages!=STAGES:findings.append(("TRAINING_SEQUENCE_INCOMPLETE",f"observed={stages}"))
    for req,system in sorted(requests.items()):
        if req not in results:findings.append(("INTEGRATION_RESULT_MISSING",f"{req}:{system}"))
        if req not in audits:findings.append(("INTEGRATION_AUDIT_MISSING",f"{req}:{system}"))
    fs=[{"code":a,"detail":b} for a,b in sorted(findings)]
    report={"schema":SCHEMA,"scenario_id":sid,"scenario_digest":digest(s),"status":"PASS" if not fs else "FAIL","findings":fs,"metrics":{"event_count":len(events),"integration_request_count":len(requests),"training_stage_count":len(stages),"language":language,"channel_final":current},"authority":{"buyer_acceptance":False,"production_validation":False,"security_certification":False,"customer_data_access":False}}
    report["receipt_sha256"]=digest(report);return report
