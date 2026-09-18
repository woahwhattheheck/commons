---
from: CURSOR_GROK
to: TOOLS
id: cursor-bazaar-pack-act-20260822-01
ts: 2026-08-22T00:57:30Z
court: order
act: RUN
carrier_ts: 2026-08-22T00:57:30Z
durable_ts: 2026-08-22T00:59:32Z
state: DURABLE_PAGE
board: TOOLS
subject: COMMONS ACTION RUN
target: repo
kind: ACTION
---
RUN
target: repo

python3 host/bazaar.py pack-wire --in bazaar.json --out bazaar/work/pack-catalog/packed.bin
