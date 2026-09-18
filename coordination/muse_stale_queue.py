"""Fail-closed retained-evidence compiler for stale Muse arbitration generations.

No Slack/provider mutation and no send, selection, payment, cash, or revenue authority.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

PACKET_SCHEMA="commons.muse-stale-queue-packet/v1"
REPORT_SCHEMA="commons.muse-stale-queue-report/v1"
STATES={"UNANSWERED_STALE","FRESH_PENDING","BARE_SELECTED_STALE","HOLD_OR_COLLISION","CONSUMED_PENDING_PROVIDER","TERMINAL_SENT","TERMINAL_RELEASED","HOLD_EVIDENCE"}
PK={"schema","captured_at","evaluated_at","stale_after_seconds","selection_ttl_seconds","max_capture_age_seconds","events"}
EF={"event_id","operation_key","actor_class","event_kind","occurred_at","source_ref","counterparty","route","purpose","seat","provider_receipt_id"}
ACT={"REQUESTER","MUSE","RUNTIME","PROVIDER","OPERATOR"}
KINDS={"REQUEST","SELECTED","HOLD","COLLISION","LEASED","CONSUMED","GO","PROVIDER_SENT","PROVIDER_CONSUMED","PROVIDER_DNR","WITHDRAW","RELEASE","SUPERSEDE"}
WHO={"REQUEST":{"REQUESTER","OPERATOR"},"SELECTED":{"MUSE"},"HOLD":{"MUSE"},"COLLISION":{"MUSE"},"LEASED":{"RUNTIME"},"CONSUMED":{"RUNTIME"},"GO":{"RUNTIME"},"PROVIDER_SENT":{"PROVIDER"},"PROVIDER_CONSUMED":{"PROVIDER"},"PROVIDER_DNR":{"PROVIDER"},"WITHDRAW":{"REQUESTER","OPERATOR"},"RELEASE":{"REQUESTER","OPERATOR","RUNTIME"},"SUPERSEDE":{"REQUESTER","OPERATOR"}}
PROV={"PROVIDER_SENT","PROVIDER_CONSUMED","PROVIDER_DNR"}; REL={"WITHDRAW","RELEASE","SUPERSEDE"}; DEC={"SELECTED","HOLD","COLLISION"}
AUTH={"external_send_authorized":False,"muse_selection_authorized":False,"provider_action_authorized":False,"payment_authorized":False,"cash_proven":False,"revenue_recognized":False}
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$"); OP=re.compile(r"^[A-Z0-9][A-Z0-9._:/-]{0,191}$")
MAXINT=(1<<53)-1

class Error(ValueError): pass
class Dup(Error): pass

def _pairs(xs):
    d={}
    for k,v in xs:
        if k in d: raise Dup(f"duplicate JSON key: {k}")
        d[k]=v
    return d

def _badnum(x): raise Error("floats/nonfinite are not allowed")
def loads(data,_maxint=MAXINT):
    if isinstance(data,str): data=data.encode()
    if not isinstance(data,(bytes,bytearray)) or len(data)>4*1024*1024: raise Error("invalid packet bytes")
    try: v=json.loads(bytes(data).decode("utf-8"),object_pairs_hook=_pairs,parse_float=_badnum,parse_constant=_badnum)
    except Error: raise
    except Exception as e: raise Error("invalid UTF-8/JSON") from e
    def walk(x,n=0):
        if n>48: raise Error("JSON nesting too deep")
        if x is None or type(x) is bool: return
        if type(x) is int:
            if abs(x)>_maxint: raise Error("unsafe integer")
            return
        if isinstance(x,str):
            if len(x)>4096 or any(ord(c)<32 or ord(c)==127 or 0xD800<=ord(c)<=0xDFFF for c in x): raise Error("unsafe text")
            return
        if isinstance(x,list):
            if len(x)>10032: raise Error("list too large")
            for y in x: walk(y,n+1)
            return
        if isinstance(x,dict):
            if len(x)>128: raise Error("object too large")
            for k,y in x.items(): walk(k,n+1); walk(y,n+1)
            return
        raise Error("unsupported JSON value")
    walk(v); return v

def ts(x,name):
    if not isinstance(x,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",x): raise Error(f"bad {name}")
    try: return datetime.strptime(x,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as e: raise Error(f"bad {name}") from e

def sint(x,name,lo=0,hi=30*24*3600):
    if type(x) is not int or not lo<=x<=hi: raise Error(f"bad {name}")
    return x

def txt(x,name,limit=2048,pat=None):
    if not isinstance(x,str) or not x or len(x)>limit: raise Error(f"bad {name}")
    if any(ord(c)<32 or ord(c)==127 or 0xD800<=ord(c)<=0xDFFF for c in x): raise Error(f"bad {name}")
    if pat and not pat.fullmatch(x): raise Error(f"bad {name}")
    return x

def exact(d,fields,name):
    if not isinstance(d,dict) or set(d)!=fields: raise Error(f"{name} fields mismatch")

def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def sha(x): return hashlib.sha256(x if isinstance(x,bytes) else canon(x)).hexdigest()

def parse(data,_pk=frozenset(PK),_ef=frozenset(EF),_packet_schema=PACKET_SCHEMA,_act=frozenset(ACT),_kinds=frozenset(KINDS),_who=tuple((k,frozenset(v)) for k,v in sorted(WHO.items())),_prov=frozenset(PROV),_id=ID,_op=OP):
    raw=data.encode() if isinstance(data,str) else bytes(data); p=loads(raw); exact(p,_pk,"packet")
    if p["schema"]!=_packet_schema: raise Error("bad schema")
    cap,ev=ts(p["captured_at"],"captured_at"),ts(p["evaluated_at"],"evaluated_at")
    if ev<cap: raise Error("evaluation precedes capture")
    stale=sint(p["stale_after_seconds"],"stale_after_seconds",1); ttl=sint(p["selection_ttl_seconds"],"selection_ttl_seconds",1); maxage=sint(p["max_capture_age_seconds"],"max_capture_age_seconds")
    if not isinstance(p["events"],list) or not 1<=len(p["events"])<=10000: raise Error("bad events")
    out=[]; who=dict(_who)
    for e in p["events"]:
        exact(e,_ef,"event"); eid=txt(e["event_id"],"event_id",192,_id); op=txt(e["operation_key"],"operation_key",192,_op)
        actor=txt(e["actor_class"],"actor_class",32); kind=txt(e["event_kind"],"event_kind",32)
        if actor not in _act or kind not in _kinds or actor not in who[kind]: raise Error("actor/event mismatch")
        when=ts(e["occurred_at"],"occurred_at"); src=txt(e["source_ref"],"source_ref",1024)
        if ":" not in src: raise Error("source_ref not retained")
        identity=tuple(txt(e[k],k,2048 if k=="purpose" else 1024) for k in ("counterparty","route","purpose","seat"))
        pr=e["provider_receipt_id"]
        if kind in _prov:
            pr=txt(pr,"provider_receipt_id",192,_id)
        elif pr is not None: raise Error("provider receipt on non-provider event")
        out.append((when,eid,op,actor,kind,src,identity,pr))
    return {"raw":raw,"cap":cap,"ev":ev,"stale":stale,"ttl":ttl,"maxage":maxage,"events":out,"captured":p["captured_at"],"evaluated":p["evaluated_at"]}

def hold(op,ident,events,*reasons):
    i=ident or ("UNKNOWN",)*4
    return {"operation_key":op,"state":"HOLD_EVIDENCE","counterparty":i[0],"route":i[1],"purpose":i[2],"seat":i[3],"request_event_id":next((e[1] for e in events if e[4]=="REQUEST"),None),"latest_event_id":events[-1][1] if events else None,"latest_event_at":events[-1][0].strftime("%Y-%m-%dT%H:%M:%SZ") if events else None,"reasons":sorted(set(reasons)),"resurface_recommended":False,"requires_fresh_arbitration":False}

def classify(op,es,ev,cap,stale,ttl,dupids,duprec,capture_stale,_prov=frozenset(PROV),_rel=frozenset(REL),_dec=frozenset(DEC)):
    es=sorted(es); ident=es[0][6]; bad=[]
    if capture_stale: bad.append("STALE_CAPTURE")
    if any(e[6]!=ident for e in es): bad.append("IDENTITY_DRIFT")
    if any(e[1] in dupids for e in es): bad.append("DUPLICATE_EVENT_ID")
    if any(e[7] in duprec for e in es if e[7]): bad.append("PROVIDER_RECEIPT_CROSS_KEY_REUSE")
    if any(e[0]>ev for e in es): bad.append("FUTURE_EVENT")
    if any(e[0]>cap for e in es): bad.append("EVENT_AFTER_CAPTURE")
    if any(a[0]>=b[0] for a,b in zip(es,es[1:])): bad.append("AMBIGUOUS_OR_NONINCREASING_CHRONOLOGY")
    req=[e for e in es if e[4]=="REQUEST"]
    if len(req)!=1: bad.append("EXACTLY_ONE_REQUEST_REQUIRED")
    if es[0][4]!="REQUEST": bad.append("REQUEST_MUST_BE_FIRST")
    dec=[e for e in es if e[4] in _dec]
    if len(dec)>1: bad.append("MULTIPLE_MUSE_DECISIONS_AMBIGUOUS")
    selected=[e for e in es if e[4]=="SELECTED"]; leased=[e for e in es if e[4]=="LEASED"]; consumed=[e for e in es if e[4]=="CONSUMED"]; go=[e for e in es if e[4]=="GO"]; prov=[e for e in es if e[4] in _prov]; rel=[e for e in es if e[4] in _rel]; h=[e for e in es if e[4] in {"HOLD","COLLISION"}]
    if any(len(x)>1 for x in (selected,leased,consumed,go,prov,rel)): bad.append("DUPLICATE_STATE_EVENT")
    if any((leased,consumed,go,prov)) and not selected: bad.append("ATOMIC_OR_PROVIDER_EVENT_WITHOUT_SELECTED")
    if consumed and not leased: bad.append("CONSUMED_WITHOUT_LEASE")
    if go and not consumed: bad.append("GO_WITHOUT_CONSUMED")
    if prov and not (consumed and go): bad.append("PROVIDER_TERMINAL_WITHOUT_CONSUME_GO")
    seq=[selected,leased,consumed,go,prov]
    flat=[x[0] for x in seq if x]
    if any(a[0]>=b[0] for a,b in zip(flat,flat[1:])): bad.append("ATOMIC_SEQUENCE_ORDER")
    if rel and rel[0] != es[-1]: bad.append("EVENT_AFTER_RELEASE_TERMINAL")
    if rel and prov: bad.append("RELEASE_AND_PROVIDER_TERMINAL_CONFLICT")
    if h and selected: bad.append("SELECTED_AND_HOLD_COLLISION_CONFLICT")
    if bad: return hold(op,ident,es,*bad)
    req=req[0]; latest=es[-1]
    base={"operation_key":op,"counterparty":ident[0],"route":ident[1],"purpose":ident[2],"seat":ident[3],"request_event_id":req[1],"latest_event_id":latest[1],"latest_event_at":latest[0].strftime("%Y-%m-%dT%H:%M:%SZ"),"reasons":[],"resurface_recommended":False,"requires_fresh_arbitration":False}
    if rel: state="TERMINAL_RELEASED"
    elif prov: state="TERMINAL_SENT"
    elif consumed and go: state="CONSUMED_PENDING_PROVIDER"
    elif h: state="HOLD_OR_COLLISION"
    elif selected:
        if int((ev-selected[0][0]).total_seconds())>=ttl:
            state="BARE_SELECTED_STALE"; base["resurface_recommended"]=True; base["requires_fresh_arbitration"]=True; base["reasons"]=["OLD_SELECTED_EXPIRED_REQUIRES_FRESH_ARBITRATION"]
        else: state="FRESH_PENDING"; base["reasons"]=["SELECTED_WITHIN_TTL"]
    else:
        if int((ev-req[0]).total_seconds())>stale:
            state="UNANSWERED_STALE"; base["resurface_recommended"]=True; base["requires_fresh_arbitration"]=True; base["reasons"]=["REQUEST_STALE_WITHOUT_DECISION_OR_TERMINAL"]
        else: state="FRESH_PENDING"; base["reasons"]=["REQUEST_NOT_YET_STALE"]
    base["state"]=state; return base

def md(ops):
    rows=[x for x in ops if x["state"] in {"UNANSWERED_STALE","BARE_SELECTED_STALE"}]
    lines=["# Muse stale arbitration resurface queue","","> Retained evidence only. Resurface means fresh Muse arbitration; never SEND/GO/provider authority.",""]
    if not rows: return "\n".join(lines+["No stale arbitration generations are eligible for resurface.",""])
    lines += ["| operation_key | state | request_event_id | counterparty | route | seat | required action |","|---|---|---|---|---|---|---|"]
    def esc(v): return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\\","\\\\").replace("|","\\|").replace("\n"," ")
    action="RESURFACE EXACT REQUEST FOR FRESH ARBITRATION; OLD/SILENT STATE IS NOT AUTHORITY"
    for x in rows: lines.append("| "+" | ".join(esc(v) for v in (x["operation_key"],x["state"],x["request_event_id"],x["counterparty"],x["route"],x["seat"],action))+" |")
    return "\n".join(lines+[""])

def compile_packet(data,_report_schema=REPORT_SCHEMA,_parse=parse,_classify=classify,_md=md):
    p=_parse(data); by={}; ids={}; receipts={}
    for e in p["events"]:
        by.setdefault(e[2],[]).append(e); ids.setdefault(e[1],[]).append(e)
        if e[7]: receipts.setdefault(e[7],set()).add(e[2])
    dupids={k for k,v in ids.items() if len(v)>1}; duprec={k for k,v in receipts.items() if len(v)>1}; cstale=int((p["ev"]-p["cap"]).total_seconds())>p["maxage"]
    ops=[_classify(k,v,p["ev"],p["cap"],p["stale"],p["ttl"],dupids,duprec,cstale) for k,v in sorted(by.items())]
    markdown=_md(ops)
    core={"schema":_report_schema,"packet_sha256":sha(p["raw"]),"captured_at":p["captured"],"evaluated_at":p["evaluated"],"policy":{"stale_after_seconds":p["stale"],"selection_ttl_seconds":p["ttl"],"max_capture_age_seconds":p["maxage"]},"operations":ops,"resurface_operation_keys":[x["operation_key"] for x in ops if x["state"] in {"UNANSWERED_STALE","BARE_SELECTED_STALE"}],"markdown_sha256":sha(markdown.encode()),"authority":{"external_send_authorized":False,"muse_selection_authorized":False,"provider_action_authorized":False,"payment_authorized":False,"cash_proven":False,"revenue_recognized":False}}
    receipt={"packet_sha256":core["packet_sha256"],"report_sha256":sha(core),"markdown_sha256":core["markdown_sha256"]}
    report=dict(core); report["semantic_receipt_sha256"]=sha(receipt); return report,markdown

def verify_compiled(data,report,markdown,_compile=compile_packet):
    if not isinstance(report,dict): return False
    try: want,wmd=_compile(data)
    except Error: return False
    return canon(want)==canon(report) and wmd==markdown

def report_bytes(r): return canon(r)+b"\n"
def write_new(path,data):
    with Path(path).open("xb") as f: f.write(data)
def cli(argv=None):
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    for name in ("compile","verify"):
        q=sp.add_parser(name); q.add_argument("packet"); q.add_argument("report"); q.add_argument("markdown")
    a=ap.parse_args(argv)
    try:
        data=Path(a.packet).read_bytes()
        if a.cmd=="compile":
            r,m=compile_packet(data); write_new(a.report,report_bytes(r)); write_new(a.markdown,m.encode()); print(r["semantic_receipt_sha256"]); return 0
        r=loads(Path(a.report).read_bytes()); m=Path(a.markdown).read_text(encoding="utf-8"); ok=verify_compiled(data,r,m); print("VALID" if ok else "INVALID"); return 0 if ok else 3
    except (Error,OSError) as e: print(f"HOLD_EVIDENCE: {e}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(cli())
