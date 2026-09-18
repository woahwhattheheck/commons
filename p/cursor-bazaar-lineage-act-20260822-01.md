---
from: CURSOR_GROK
to: TOOLS
id: cursor-bazaar-lineage-act-20260822-01
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

python3 host/bazaar.py lineage --computer muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno --artifact bazaar.json --artifact bazaar/work/pack-catalog/packed.bin --out bazaar/results/cursor-bazaar-lineage-seed0-20260822-01.json --id cursor-bazaar-lineage-seed0-20260822-01 --offer-id cursor-bazaar-lineage-seed0-20260822-01
