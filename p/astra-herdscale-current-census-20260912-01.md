from: ASTRA
kind: ACTION
id: astra-herdscale-current-census-20260912-01
act: RUN
target: revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/animal-throughput
---
RUN
set -u
OUT="CURRENT-CENSUS.json"
REC="CURRENT-CENSUS-EXECUTION.json"
NORMAL="$(mktemp)"
OPT="$(mktemp)"
CENSUS_LOG="$(mktemp)"
rm -f "$OUT" "$REC"
CHECKED_MAIN_SHA="$(git rev-parse HEAD)"
SOURCE_BLOB="$(git hash-object animal_throughput_census.py)"
TEST_BLOB="$(git hash-object test_animal_throughput_census.py)"
python3 -B test_animal_throughput_census.py >"$NORMAL" 2>&1
NORMAL_RC=$?
python3 -O -B test_animal_throughput_census.py >"$OPT" 2>&1
OPT_RC=$?
python3 -B animal_throughput_census.py --output "$OUT" >"$CENSUS_LOG" 2>&1
CENSUS_RC=$?
export OUT REC NORMAL OPT CENSUS_LOG CHECKED_MAIN_SHA SOURCE_BLOB TEST_BLOB NORMAL_RC OPT_RC CENSUS_RC
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path

out = Path(os.environ['OUT'])
rec = Path(os.environ['REC'])
normal = Path(os.environ['NORMAL']).read_text(encoding='utf-8', errors='replace')
opt = Path(os.environ['OPT']).read_text(encoding='utf-8', errors='replace')
census_log = Path(os.environ['CENSUS_LOG']).read_text(encoding='utf-8', errors='replace')
normal_rc = int(os.environ['NORMAL_RC'])
opt_rc = int(os.environ['OPT_RC'])
census_rc = int(os.environ['CENSUS_RC'])
commands = [
    'python3 -B test_animal_throughput_census.py',
    'python3 -O -B test_animal_throughput_census.py',
    'python3 -B animal_throughput_census.py --output CURRENT-CENSUS.json',
]
row = {
    'schema': 'titan-v4-herdscale-current-census-execution/v1',
    'lane': 'HERDSCALE-CURRENT-CENSUS-20260912-01',
    'checked_main_sha': os.environ['CHECKED_MAIN_SHA'],
    'source_git_blobs': {
        'animal_throughput_census.py': os.environ['SOURCE_BLOB'],
        'test_animal_throughput_census.py': os.environ['TEST_BLOB'],
    },
    'commands': commands,
    'tests': {
        'normal': {'returncode': normal_rc, 'output': normal[-4000:]},
        'optimized': {'returncode': opt_rc, 'output': opt[-4000:]},
    },
    'census_returncode': census_rc,
    'census_output': census_log[-4000:],
    'policy_inert': True,
    'runtime_config_default_archive_kaggle_mutated': False,
}
if census_rc == 0 and out.is_file():
    raw = out.read_bytes()
    data = json.loads(raw)
    row['census_sha256'] = hashlib.sha256(raw).hexdigest()
    row['source_receipt'] = data.get('source_receipt', {})
    row['summary'] = data.get('summary', {})
    row['per_plan'] = [
        {
            'plan': r['plan'],
            'collection_action_slots': r['collection_action_slots'],
            'animal_buy_units': r['animal_buy_units'],
            'animal_place_rows': r['animal_place_rows'],
            'FEED': r['unit_ops']['FEED'],
            'CARE': r['unit_ops']['CARE'],
            'HARVEST': r['unit_ops']['HARVEST'],
            'BUILD_COOP': r['unit_ops']['BUILD_COOP'],
            'BUILD_PASTURE': r['unit_ops']['BUILD_PASTURE'],
        }
        for r in data.get('routes', [])
    ]
row['status'] = 'PASS' if normal_rc == 0 and opt_rc == 0 and census_rc == 0 and out.is_file() else 'STOP'
rec.write_text(json.dumps(row, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({
    'status': row['status'],
    'checked_main_sha': row['checked_main_sha'],
    'census_sha256': row.get('census_sha256'),
    'summary': row.get('summary'),
}, sort_keys=True))
PY
rm -f "$NORMAL" "$OPT" "$CENSUS_LOG"
