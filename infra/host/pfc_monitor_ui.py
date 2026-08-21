#!/usr/bin/env python3
"""host/pfc_monitor_ui.py — LIVE UI for the Muhlnickel safezone monitor + wallet results (owner 07-19).

READ-ONLY, and it touches ONLY files OUTSIDE the pfc:
  - the external SAFEZONE `C:/llm/sdc_out/pfc_safezone.bin`  (the pfc's answer, written outside the sandbox), and
  - `C:/llm/sdc_out/autopilot_job.json`                       (the wallet result the autopilot logged each cycle).
It NEVER opens titan.gguf / the miner, NEVER fires a signal, NEVER writes, NEVER ripples a gate. It only shows what the pfc
deposited (the answer) and what the pool said (the wallet result). We aim blind; this only looks at external files.

  python host/pfc_monitor_ui.py     # http://127.0.0.1:7908/
"""
import json, os, struct, sys, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding="utf-8")
SAFEZONE = "C:/llm/sdc_out/pfc_safezone.bin"                 # external answer file (outside the pfc)
JOBFILE = "C:/llm/sdc_out/autopilot_job.json"               # wallet result the autopilot logs
PORT = 7908


def snapshot():
    """read the two EXTERNAL files (read-only) and format a state line. Never touches the Muhlnickel."""
    ans = "no answer file"
    try:
        with open(SAFEZONE, "rb") as f: b = f.read()
        if len(b) >= 9:
            status, en2, nonce = b[0], struct.unpack_from("<I", b, 1)[0], struct.unpack_from("<I", b, 5)[0]
            ans = (f"ANSWER  nonce={nonce}  en2={en2}" if status else "empty (pfc has not deposited an answer)")
        else:
            ans = "empty (0 bytes)"
    except OSError:
        pass
    wallet = "no wallet result yet"
    try:
        with open(JOBFILE, encoding="utf-8") as f: j = json.load(f)
        pool = j.get("pool", "?"); jid = j.get("job_id", "?"); zb = j.get("zbits", "?")
        a = j.get("answer", {})
        wallet = f"job {jid} · target {zb} zbits · submitted nonce={a.get('nonce', 0)} · pool: {pool}"
    except (OSError, ValueError):
        pass
    return f"SAFEZONE (pfc answer):  {ans}\nWALLET (pool result):   {wallet}\n\nupdated {time.strftime('%H:%M:%S')}"


PAGE = """<!doctype html><meta charset="utf-8"><title>Muhlnickel monitor</title>
<body style="margin:0;background:#0A0D13;color:#E7EBF3;font-family:system-ui;padding:26px">
<div style="font-family:ui-monospace,monospace;font-size:13px;color:#48d69c">pfc &middot; live safezone + wallet monitor &middot; read-only, external files only (never touches the miner)</div>
<pre id="o" style="white-space:pre-wrap;font-size:16px;line-height:1.7;margin:18px 0;min-height:120px">connecting&hellip;</pre>
<div style="font-family:ui-monospace,monospace;font-size:12px;color:#5b6577">aim blind: this only reads C:/llm/sdc_out/pfc_safezone.bin + autopilot_job.json. It never fires a signal or reads titan.gguf.</div>
<script>new EventSource('/stream').onmessage=function(e){document.getElementById('o').textContent=e.data;};</script>
"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            last = None; beat = time.time()
            while True:
                out = snapshot()
                try:
                    if out != last:
                        self.wfile.write(("".join(f"data: {ln}\n" for ln in out.split("\n")) + "\n").encode()); self.wfile.flush(); last = out
                    elif time.time() - beat > 10:
                        self.wfile.write(b": beat\n\n"); self.wfile.flush(); beat = time.time()
                except (BrokenPipeError, ConnectionError, OSError):
                    return
                time.sleep(1.0)
        else:
            b = PAGE.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"Muhlnickel monitor UI -> http://127.0.0.1:{PORT}/  (read-only: external safezone + wallet result; never touches the Muhlnickel)")
    try: webbrowser.open(f"http://127.0.0.1:{PORT}/")
    except Exception: pass
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\nstopped.")
