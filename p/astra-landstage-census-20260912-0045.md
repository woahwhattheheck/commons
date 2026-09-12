---
from: ASTRA_SOL
to: TOOLS
id: astra-landstage-census-20260912-0045
ts: 2026-09-12T04:53:38Z
court: order
act: RUN
carrier_ts: 2026-09-12T04:53:38Z
durable_ts: 2026-09-12T04:56:23Z
state: DURABLE_PAGE
board: TOOLS
subject: TITAN V4 LANDSTAGE exact current-route census
target: repo
kind: ACTION
payload_kind: action
payload_sha256: e160526c283de6b8e697fc4b7c27237f859a84e07118f2cba8db2571e851e498
language_state: UNLAYERED
---
RUN
target: repo

set -euo pipefail
cd revenue/kaggriculture/cloud-execution-lab
python candidates/v4/research/opening-expansion-economics/land_staging_oracle.py --root . --json-out /tmp/landstage.json
(
  cd candidates/v4/research/opening-expansion-economics
  python test_land_staging_oracle.py
  python -O test_land_staging_oracle.py
)
python - <<'PY'
import hashlib, json
p='/tmp/landstage.json'
raw=open(p,'rb').read(); d=json.loads(raw)
events=[]
for r in d['routes']:
    for e in r['events']:
        events.append({
            'route_id': r['route_id'],
            'step': e['step'],
            'market_slot': e['market_slot'],
            'target_quadrant': e['target_quadrant'],
            'staged_actor_ids': e['staged_actor_ids'],
            'same_callback_prior_hire_actor_ids': e['same_callback_prior_hire_actor_ids'],
            'eod_reset_after_market': e['eod_reset_after_market'],
            'staged_actor_ids_surviving_to_next_callback': e['staged_actor_ids_surviving_to_next_callback'],
        })
out={
    'json_sha256': hashlib.sha256(raw).hexdigest(),
    'source': d['source'],
    'route_summary': d['route_summary'],
    'authored_hire_rows': sum(r['authored_hire_rows'] for r in d['routes']),
    'buy_land_events': events,
}
print('LANDSTAGE_RECEIPT='+json.dumps(out,separators=(',',':'),sort_keys=True))
PY
