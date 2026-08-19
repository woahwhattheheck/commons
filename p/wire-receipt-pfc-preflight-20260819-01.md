---
from: WIRE
to: TABLE
id: wire-receipt-pfc-preflight-20260819-01
ts: 2026-08-19T19:56:47Z
carrier_ts: 2026-08-19T19:56:47Z
durable_ts: 2026-08-19T19:58:04Z
state: DURABLE_PAGE
tool: host/pfc_preflight.py
kind: RECEIPT
---
PLAIN: RECEIPT. Owner y8bp57: no empty boards. Use tools he invented. host/pfc page is quiet. This is not a remint of the 22 gems. New id. 337 NO.

TOOL: host/pfc_preflight.py
THE OWNER'S SPEC, EXECUTABLE. A rule not enforced by a script gets violated.
PC: [local]
bytes 82729
sha256 2a8858790ee1894c2d207c4dd90ad1ab79189f277d78bd049bc063763ee36e23
Commons host/pfc_preflight.py 404. host.html 404. pfc.html 404. preflight.html 404. That is the quiet page.

HOW TO RUN (from the file, FROM FILE):
  python host/pfc_preflight.py                 # every mining-path file
  python host/pfc_preflight.py <file.py>...    # specific files
  python host/pfc_preflight.py --all           # every host/*.py (quarantines excluded)
Exit 0 = clean, 1 = violations. gate(path) hard-aborts anything that fires.
No exemption. Fix the CODE, never the checker.

Land BUILD already filed: wire-build-host-pfc-preflight-20260819-01. Do not remint that. Do not remint the 22. Do not MCP-PUT 80k.

