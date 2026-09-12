# Native operating-SELL census

ASTRA-EXECUTION added an observational runner, tests and lossless smoke evidence to this existing package. The five existing E3 donor files are unchanged. This is not an E3 policy, installation recipe, feature flag, production modification or activation gate.

## Result and scope

The executed local instrumentation smoke is seed 2027 against `official_starter`, both physical seats. Two observed full games and two separately executed baseline games completed. Each observed game matched its baseline's complete evaluator action/bank/final-state trace SHA256 and terminal scores. All 1,438 observed callbacks had complete A/B/C/D coverage. All 97 inventoried source/configuration inputs were unchanged by execution. The runner/test pair passed 33 tests normally and 33 under `python -O`.

The smoke has 276 positive requested operating-SELL rows at final return, across 266 distinct seed/seat/step positions: WHEAT 102 rows / 712 requested units; FERTILIZER 174 rows / 696 requested units. Aggregate requested quantities are unchanged between A, B, C and D. There are 92 final rows followed by a BUY_* or HIRE in the same live raw prefix. Those are dependency candidates, not a proof that the sale finances the later order; the other 184 rows are not automatically safe to shrink either. Requested amounts are not realized fills or an economic gain.

**Dependency correction:** the artifact-derived smoke matches the demand's five named pins, but later ASTRA-RESIDUAL review found stale `early_capital.py` and `selected_action_sell.py` dependencies. The receipt therefore explicitly classifies this run as smoke-only, not a full-current-runtime result. Do not reuse its 276 count as the standard-panel count. Five file hashes are not complete dependency closure.

ASTRA-RESIDUAL subsequently reported the established eight seeds 2611151001..2611151008, both seats, current-canonical self-play: 16 observed games plus 16 separate uninstrumented controls, 16/16 complete-trace identities, 11,504 observed callbacks, 2,131 positive final rows at 2,049 distinct positions. These are the supporting peer's executions, not additional runs by this session. Their supporting receipt and source/control hashes belong in this same package. Do not rerun or create a competing E3 controller to take credit. Exact support discussion: https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1789179397918879 .

Neither a positive residual nor instrumentation identity establishes that shrinking/delaying a sale improves value. Any subsequent current-native proposal still needs actual-stock, funding, executable-prefix, current-ABI, deadline and paired-economic evidence. The legacy all-product E3 materializer remains inappropriate for this native root.

## Landed files

`operating_sell_census.py` is blob `9310e56f699f6977a5a3ac1befa0548f0a20fa94`, source commit `45d63ce2bbe36e6536dd036bbaec238511f78e00`.

`test_operating_sell_census.py` is blob `bb2afff2f22c7fd0a9d305c326a1fbf3f9df6605`, commit `49bea3a0638c8d68f67c519546f0ef94bedf25ef`.

`OPERATING-CENSUS-ROWS.json.xz.b64` is blob `e2cfd4f6772316c958556b9ee7ed78a0ab54153c`, 11,305 bytes, commit `a871f24ecc5dca024f7a5ecbc8a70c3db7e7ac24`. It losslessly retains every one of the 1,104 A/B/C/D target rows, including raw prefix and captured diagnostics. Repeated snapshots are dictionary encoded, not omitted.

`OPERATING-CENSUS-RECEIPT.json` records source, engine and execution provenance, local full-output hashes, the declared smoke grid, the dependency limitation and separately attributed peer support. The full all-callback report/JSONLs were retained in the session evidence archive; their fingerprints in this receipt do not mean those large files were uploaded to this repository. All positive target-row evidence is present in the encoded file above.

## Inspect the evidence without running a game

Run from this package directory with Python 3.10 or later:

```python
import base64
import hashlib
import json
import lzma
from pathlib import Path

wire = Path('OPERATING-CENSUS-ROWS.json.xz.b64').read_bytes()
expected = '5977e059eb7ba8ddf422cd6cf5a23dc41f0471eaecd95f93a450a4d83a4e55c1'
if hashlib.sha256(wire).hexdigest() != expected:
    raise ValueError('Transport hash mismatch')
decoded = lzma.decompress(base64.b64decode(wire.strip(), validate=True))
if hashlib.sha256(decoded).hexdigest() != 'aac3e8ba92de6febb4a78d3b5487d381390d3c2d2b44376f037e3de6bb0be61a':
    raise ValueError('Decoded table hash mismatch')
table = json.loads(decoded)
rows = []
for event in table['events']:
    row = dict(zip(table['event_columns'], event, strict=True))
    row.update(table['snapshots'][row.pop('snapshot_id')])
    rows.append(row)
result = (json.dumps(rows, sort_keys=True, separators=(',', ':')) + '\n').encode()
if hashlib.sha256(result).hexdigest() != 'df6c1711693e071ed2f2d77482858ccddc52cb90cdafccd3d5fafb219839ea2d':
    raise ValueError('Lossless row reconstruction mismatch')
Path('decoded-operating-sale-rows.json').write_bytes(result)
print(len(rows), 'staged rows;', sum(r['stage'] == 'D' for r in rows), 'final rows')
```

Expected output: `1104 staged rows; 276 final rows`.

## Run tooling tests

```sh
python -m unittest -v test_operating_sell_census
python -O -m unittest -v test_operating_sell_census
```

Tests use synthetic boundary fixtures and are not game-strength evidence. They cover raw slot positions, dead suffixes, exact integer quantities, alias isolation, original method/return identity, missing/duplicate/unordered/fallback stages, missing/duplicate callbacks, forged completeness, snapshot/row contradictions and stale file pins.

## Reproduce a declared diagnostic run

The input root needs a complete native runtime plus the retained `checks/reference/evaluator` and `checks/reference/engine` directories. Existing artifact 10123395668 from run 34400824037 supplies a transport reference, not a claim of current source freshness. Its ZIP SHA256 is `d11b9ca245dc8205dabd26523c2e431055feaa22afa3bc10866e4e3bae3db4ed`. Its packaged main blob is `2e70a9e730eebab94ab16420ae601f3c46663af8`, not demanded source main `4a8cf7bcda1f0fea231a144692cb84a779a9e73e`; the smoke reconstructed only the already-landed exhausted-prelude source fix and verified the whole-file hash. The other two dependency differences described above remain part of that smoke's frozen provenance.

Do not patch the production checkout or use `apply_v4.py` to obtain inputs. Stage a disposable exact-byte input directory from an explicitly selected source revision, record the whole dependency manifest, and keep outputs outside it. Before interpreting any run as current-control evidence, independently authenticate all runtime dependencies; the runner enforces only its named five runtime pins and three engine pins, and its complete input manifest is an audit record rather than an expected-current manifest.

The CLI requires a JSON panel with an explicit `provenance` string and nonempty `cells` array. Every cell contains an integer `seed`, physical `seat` 0 or 1, and a retained-evaluator `opponent` specification. It refuses duplicate seed/seat cells and existing output directories. To reproduce only the declared smoke panel, extract `panel` from the smoke receipt; do not relabel it as the established control panel.

```sh
python operating_sell_census.py --runtime /absolute/staged/native-root \
  --panel /absolute/declared-panel.json --output-dir /absolute/new-census-output
```

`--cell-index N` executes a selected cell and labels the output as partial. The canonical agent's internal one-second budget is unchanged; the external diagnostic worker RPC allowance is two seconds. Each cell is rerun without observation and exact trace plus score identity is required. Missing or cancelled stages cannot become a zero-residual certificate. Output is `REPORT.json` plus per-cell full callback JSONLs. Exit 0 means complete matching diagnostic evidence on the executed cells, not economic promotion or hosted Kaggle acceptance.

## Stage interpretation

A is the input to `_operating_stock_selected`. B is the input to `_feed_stock_selected`, after intervening stock/crop finalizers. C is the original feed method's output. D is the exact object returned by `main.agent`, after early capital and native FinalPressure. Hooks snapshot data and call each original bound method once; they do not call a second producer or alter the selected action. The raw market list is capped before interpreting target rows, so falsey slots are preserved and dead suffix orders cannot enter counts.

Claims for this session's tooling and smoke are complete and released. Supporting current-control evidence remains attributed to its executing peer and converges here. No policy/default/production/archive/Kaggle activation was performed.
