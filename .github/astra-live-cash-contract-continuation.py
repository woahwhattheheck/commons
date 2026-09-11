from pathlib import Path
import json
import subprocess

BASE_SHA = '1931a6bdd6ba8243377eee6567a30fdea895565b'
BRANCH = 'astra/live-cash-contract-continuation-20260911'
WORKFLOW = Path('.github/workflows/astra-live-cash-contract-continuation.yml')
SELF = Path('.github/astra-live-cash-contract-continuation.py')
OWNED = [
    'revenue/outcome_commerce/catalog.schema.json',
    'revenue/outcome_commerce/catalog.json',
    'test_outcome_commerce.py',
]
REPLACEMENTS = {
    '7e94f42e9a92e166f614916d63712403f6fc77f7': 'e18c2865cf737eb2c76da23012dd0a890ccca202',
    '235c94284c14c179388b5e53b4b9d0f6a8a0dd7d': '7f7d41a94333a72cbd1f641f0c437557f3a95361',
    '258734957efc727f46f6315804b6034487e98896': 'e607d3ba7cd24dd542b24a1e8be9e8579d6745ce',
    'b2c54753a82683a70831588366e35114ad644a65': 'ec94c5a6113ce6de6fd601f8bd438d5e6b117b2f',
    '4fd23e7a10e90a5c988f3581d77e83b86e212884': '885dd967197935ca69cc25482f52fea09d2c5bc3',
    '62625136a9e5abfe77d9e7afa59e8ee67571b33e': '49cc55559e93595b22bbcef15de6f74ac8e0f3f4',
    'fa4ef433b0b233bb3ddc633c1828957e5d75e453': '6fb73c5837ac37ec7f48cc6efc12cc98797f12d8',
}
SOURCE_BLOBS = {
    'land/sku-tip-20260826.md': REPLACEMENTS['7e94f42e9a92e166f614916d63712403f6fc77f7'],
    'land/sku-seat-20260826.md': REPLACEMENTS['235c94284c14c179388b5e53b4b9d0f6a8a0dd7d'],
    'land/sku-unlock-20260826.md': REPLACEMENTS['258734957efc727f46f6315804b6034487e98896'],
    'land/sku-monthly-tip-20260826.md': REPLACEMENTS['b2c54753a82683a70831588366e35114ad644a65'],
    'land/sku-boost-20260826.md': REPLACEMENTS['4fd23e7a10e90a5c988f3581d77e83b86e212884'],
    'land/sku-whitebox-hour-20260826.md': REPLACEMENTS['62625136a9e5abfe77d9e7afa59e8ee67571b33e'],
    'land/sku-muhlnickel-titan-20260826.md': REPLACEMENTS['fa4ef433b0b233bb3ddc633c1828957e5d75e453'],
}

def run(*args, capture=False):
    return subprocess.run(args, check=True, text=True, capture_output=capture)

run('git', 'fetch', 'origin', 'main')
drift = run('git', 'diff', '--name-only', f'{BASE_SHA}..origin/main', '--', *OWNED, capture=True).stdout.strip()
if drift:
    raise SystemExit(f'owned target-path drift since continuation base:\n{drift}')

schema_path = Path(OWNED[0])
catalog_path = Path(OWNED[1])
test_path = Path(OWNED[2])
schema = json.loads(schema_path.read_text(encoding='utf-8'))
catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
assert 'live_cash' not in schema['properties']
assert 'live_cash' not in schema['$defs']
assert 'live_cash_product' not in schema['$defs']
assert isinstance(catalog['live_cash'], dict) and catalog['live_cash']['products']

for path, want in SOURCE_BLOBS.items():
    got = run('git', 'hash-object', path, capture=True).stdout.strip()
    if got != want:
        raise SystemExit(f'{path}: authoritative blob drift {got} != {want}')

schema_raw = schema_path.read_text(encoding='utf-8')
top_old = '    "listings": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/listing"}}\n  },'
top_new = '    "listings": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/listing"}},\n    "live_cash": {"$ref": "#/$defs/live_cash"}\n  },'
if schema_raw.count(top_old) != 1:
    raise SystemExit(f'schema top-level anchor count={schema_raw.count(top_old)}')
schema_raw = schema_raw.replace(top_old, top_new, 1)
defs_old = '''    "string_list": {
      "type": "array",
      "uniqueItems": true,
      "items": {"type": "string", "minLength": 1}
    },
    "funnel_truth": {'''
defs_new = '''    "string_list": {
      "type": "array",
      "uniqueItems": true,
      "items": {"type": "string", "minLength": 1}
    },
    "live_cash_product": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "price_usd", "path"],
      "properties": {
        "name": {"type": "string", "minLength": 1},
        "price_usd": {"type": "integer", "minimum": 1},
        "path": {"type": "string", "minLength": 1}
      }
    },
    "live_cash": {
      "type": "object",
      "additionalProperties": false,
      "required": ["cite", "note", "products"],
      "properties": {
        "cite": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": {"type": "string", "minLength": 1}
        },
        "note": {"type": "string", "minLength": 1},
        "products": {
          "type": "array",
          "items": {"$ref": "#/$defs/live_cash_product"}
        }
      }
    },
    "funnel_truth": {'''
if schema_raw.count(defs_old) != 1:
    raise SystemExit(f'schema defs anchor count={schema_raw.count(defs_old)}')
schema_path.write_text(schema_raw.replace(defs_old, defs_new, 1), encoding='utf-8')

catalog_raw = catalog_path.read_text(encoding='utf-8')
for old, new in REPLACEMENTS.items():
    count = catalog_raw.count(old)
    if count != 1:
        raise SystemExit(f'catalog expected exactly one {old}, found {count}')
    catalog_raw = catalog_raw.replace(old, new, 1)
catalog_path.write_text(catalog_raw, encoding='utf-8')

test_raw = test_path.read_text(encoding='utf-8')
marker = 'DIAGNOSTIC_SKUS = ('
if test_raw.count(marker) != 1:
    raise SystemExit('DIAGNOSTIC_SKUS marker drift')
prefix, suffix = test_raw.split(marker, 1)
for old, new in REPLACEMENTS.items():
    count = prefix.count(old)
    if count != 1:
        raise SystemExit(f'RECORDED_STRIPE_SKUS expected exactly one {old}, found {count}')
    prefix = prefix.replace(old, new, 1)
test_path.write_text(prefix + marker + suffix, encoding='utf-8')

schema = json.loads(schema_path.read_text(encoding='utf-8'))
json.loads(catalog_path.read_text(encoding='utf-8'))
assert schema['properties']['live_cash'] == {'$ref': '#/$defs/live_cash'}
assert schema['$defs']['live_cash_product'] == {
    'type': 'object', 'additionalProperties': False,
    'required': ['name', 'price_usd', 'path'],
    'properties': {
        'name': {'type': 'string', 'minLength': 1},
        'price_usd': {'type': 'integer', 'minimum': 1},
        'path': {'type': 'string', 'minLength': 1},
    },
}
assert schema['$defs']['live_cash'] == {
    'type': 'object', 'additionalProperties': False,
    'required': ['cite', 'note', 'products'],
    'properties': {
        'cite': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': {'type': 'string', 'minLength': 1}},
        'note': {'type': 'string', 'minLength': 1},
        'products': {'type': 'array', 'items': {'$ref': '#/$defs/live_cash_product'}},
    },
}
run('python', '-m', 'py_compile', 'test_outcome_commerce.py')
run('python', '-W', 'error', '-m', 'unittest', '-q', 'test_outcome_commerce.py')
run('git', 'diff', '--check')

WORKFLOW.unlink()
SELF.unlink()
changed = run('git', 'diff', '--name-only', BASE_SHA, '--', capture=True).stdout.splitlines()
if sorted(changed) != sorted(OWNED):
    raise SystemExit(f'unexpected final path set: {changed}')

run('git', 'config', 'user.name', 'astra-continuation')
run('git', 'config', 'user.email', 'astra-continuation@users.noreply.github.com')
run('git', 'add', '-A')
run('git', 'diff', '--cached', '--check')
run('git', 'commit', '-m', 'fix(outcome-commerce): complete live-cash contract')
run('git', 'push', 'origin', f'HEAD:{BRANCH}')
