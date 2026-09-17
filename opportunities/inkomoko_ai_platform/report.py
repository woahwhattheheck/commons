from __future__ import annotations
import os,stat
from pathlib import Path
from .core import CarrierError,canonical

def render_markdown(p):
    lines=[f"# {p['opportunity']['title']}","",f"**Status:** `{p['status']}`",f"**Buyer:** {p['opportunity']['buyer']}",f"**Deadline date:** {p['opportunity']['submission_deadline_date']} (time known: {str(p['opportunity']['submission_deadline_time_known']).lower()})",f"**Source authority:** `{p['opportunity']['source_authority']}`","","## Hold / qualification reasons"]
    lines += [f"- {x}" for x in (p["hold_reasons"] or ["No hold reason at this compiled generation."])]
    lines += ["","## Mandatory requirement state"]+[f"- `{x['id']}` — `{x['evidence_state']}` — {x['description']}" for x in p["requirements"] if x["mandatory"]]
    lines += ["","## Proposed specialist workshare",f"Commercial state: `{p['specialist_workshare']['state']}` / `{p['specialist_workshare']['price_state']}`."]+[f"- `{x['id']}` — {x['description']}" for x in p["specialist_workshare"]["capabilities"]]
    lines += ["","## Authority ceiling","This artifact does not authorize buyer/partner contact, proposal submission, signature, price commitment, contract acceptance, external-system access, award/payment/revenue claims, or provider mutation.","",f"Receipt: `{p['receipt']['receipt_sha256']}`",""]
    return "\n".join(lines)

def publish(packet,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);s=os.lstat(out)
    if stat.S_ISLNK(s.st_mode) or not stat.S_ISDIR(s.st_mode):raise CarrierError("output target must be a real directory")
    paths=(out/"packet.json",out/"packet.md")
    if any(p.exists() for p in paths):raise CarrierError("refusing to overwrite existing output")
    made=[]
    try:
        for p,data in ((paths[0],canonical(packet)+b"\n"),(paths[1],render_markdown(packet).encode())):
            fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);made.append(p)
            with os.fdopen(fd,"wb") as h:h.write(data);h.flush();os.fsync(h.fileno())
    except Exception as e:
        for p in made:
            try:p.unlink()
            except OSError:pass
        if isinstance(e,CarrierError):raise
        raise CarrierError(f"publication failed: {e}") from e
    return paths
