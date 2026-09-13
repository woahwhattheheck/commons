#!/usr/bin/env python3
"""Local judge demo for the AI Builders Agent Failure Autopsy entry.

The demo is deliberately provider-free.  It exercises the real public synthetic
case through the existing fulfillment validator and renders the retained intake,
report, and validation receipt in a small local web UI.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "revenue" / "agent_failure_autopsy"
EXAMPLES = CORE / "examples"
MAX_JSON_BYTES = 2_000_000


def _read_json(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    if EXAMPLES.resolve() not in resolved.parents:
        raise ValueError("demo JSON must come from the public synthetic example directory")
    if not resolved.is_file():
        raise ValueError("demo input must be an ordinary file")
    raw = resolved.read_bytes()
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("demo JSON exceeds bounded read limit")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("demo JSON top level must be an object")
    return parsed


def validate_demo() -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(CORE / "fulfillment.py"),
        "validate",
        "--intake",
        str(EXAMPLES / "intake.json"),
        "--report",
        str(EXAMPLES / "report.json"),
        "--evidence-root",
        str(EXAMPLES),
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12_000:],
        "stderr": proc.stderr[-4_000:],
        "command": "python revenue/agent_failure_autopsy/fulfillment.py validate --intake … --report … --evidence-root …",
    }


def build_payload() -> dict[str, Any]:
    intake = _read_json(EXAMPLES / "intake.json")
    report = _read_json(EXAMPLES / "report.json")
    validation = validate_demo()
    return {
        "product": "Agent Failure Autopsy",
        "tagline": "Evidence-linked diagnosis for one failed coding-agent run.",
        "mode": "PUBLIC_SYNTHETIC_DEMO",
        "intake": intake,
        "report": report,
        "validation": validation,
        "truth": {
            "buyer_data_used": False,
            "payment_claimed": False,
            "sale_claimed": False,
            "human_review_claimed": False,
            "external_action_authorized": False,
            "note": "The synthetic report is a PEER_DRAFT. Buyer-ready delivery requires separate capable review under the commercial runbook.",
        },
    }


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Failure Autopsy · AI Builders Demo</title>
<style>
:root{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:#0b0f14;color:#eef4ff}
body{max-width:1120px;margin:0 auto;padding:32px 20px 60px}h1{font-size:clamp(2rem,6vw,4.7rem);line-height:.95;margin:.2em 0}
.kicker{letter-spacing:.14em;text-transform:uppercase;color:#9eb4ce}.lede{max-width:760px;font-size:1.08rem;line-height:1.6;color:#cbd7e6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin:28px 0}.card{border:1px solid #263241;border-radius:14px;padding:18px;background:#111923}
.badge{display:inline-block;border:1px solid #4c657e;border-radius:999px;padding:5px 10px;margin:3px;font-size:.82rem}button{font:inherit;padding:12px 16px;border-radius:10px;border:0;cursor:pointer}
pre{white-space:pre-wrap;word-break:break-word;background:#070a0e;border:1px solid #202c38;border-radius:12px;padding:16px;max-height:520px;overflow:auto}.ok{color:#8ee6a8}.bad{color:#ff9a9a}
.small{font-size:.85rem;color:#97a9bc}a{color:#a9d4ff}
</style>
</head><body>
<div class="kicker">AI Builders Hackathon 2026 · working local demo</div>
<h1>Agent Failure<br>Autopsy</h1>
<p class="lede">When a coding agent fails, the expensive part is not rerunning it. It is proving <em>where</em> the run first diverged, which cause the evidence supports, what alternatives were challenged, and what regression check should prevent recurrence.</p>
<div>
<span class="badge">one failed run</span><span class="badge">evidence-linked</span><span class="badge">adversarial challenge</span><span class="badge">peer-review gate</span><span class="badge">bounded intake</span>
</div>
<div class="grid">
<div class="card"><h2>1 · Intake</h2><p>Expected vs actual result, harness/stack, and sanitized evidence. Evidence instructions are treated as untrusted data.</p></div>
<div class="card"><h2>2 · Autopsy</h2><p>Reconstruct the run, identify first meaningful divergence, rank primary and contributing causes, challenge plausible alternatives, and bind every finding to evidence.</p></div>
<div class="card"><h2>3 · Review</h2><p>Automated output stays <strong>PEER_DRAFT</strong>. A separate capable reviewer must confirm evidence links and remove unsupported claims before buyer-ready delivery.</p></div>
</div>
<button id="run">Run the public synthetic case</button>
<p id="status" class="small">No buyer data, credentials, provider calls, or payment action are used by this demo.</p>
<div class="grid">
<div class="card"><h2>Validator receipt</h2><pre id="validation">Press Run.</pre></div>
<div class="card"><h2>Truth boundary</h2><pre id="truth">Press Run.</pre></div>
</div>
<div class="card"><h2>Synthetic intake</h2><pre id="intake">Press Run.</pre></div>
<div class="card"><h2>Synthetic report</h2><pre id="report">Press Run.</pre></div>
<p class="small">This interface is a judge/demo surface over the existing public fulfillment contract; it does not replace the commercial runbook or its independent review requirement.</p>
<script>
const pretty=x=>JSON.stringify(x,null,2);
document.querySelector('#run').addEventListener('click',async()=>{
 const status=document.querySelector('#status');status.textContent='Running exact public synthetic validation…';
 try{const r=await fetch('/api/demo',{cache:'no-store'});const p=await r.json();
 document.querySelector('#validation').textContent=pretty(p.validation);document.querySelector('#truth').textContent=pretty(p.truth);
 document.querySelector('#intake').textContent=pretty(p.intake);document.querySelector('#report').textContent=pretty(p.report);
 status.className=p.validation.ok?'ok':'bad';status.textContent=p.validation.ok?'PASS · synthetic case is internally valid under the public fulfillment contract.':'HOLD · validator rejected the synthetic case; inspect receipt.';
 }catch(e){status.className='bad';status.textContent='Demo error: '+e;}
});
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentFailureAutopsyDemo/1"

    def _send(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
            return
        if self.path == "/api/demo":
            try:
                body = json.dumps(build_payload(), sort_keys=True).encode()
                self._send(200, "application/json; charset=utf-8", body)
            except Exception as exc:  # local judge surface; fail visibly
                body = json.dumps({"error": type(exc).__name__, "detail": str(exc)}).encode()
                self._send(500, "application/json; charset=utf-8", body)
            return
        self._send(404, "application/json; charset=utf-8", b'{"error":"not_found"}')

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("demo: " + (fmt % args) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--check", action="store_true", help="run synthetic validator and exit")
    args = parser.parse_args(argv)
    if args.check:
        payload = build_payload()
        print(json.dumps(payload["validation"], indent=2, sort_keys=True))
        return 0 if payload["validation"]["ok"] else 2
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("demo binds loopback only")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Agent Failure Autopsy demo: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
