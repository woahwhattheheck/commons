# ASTRA-DOGWOOD: supplier onboarding mapper validation

Demand: `bm-hive-20260908-041`. This is an additive consumer of the existing
Supplier Reorder Assistant, not a second planner or inventory workspace.

Source claim: https://tokenjunkielabs.slack.com/archives/C0C05UVE0EA/p1788867160546909
Coordination claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788867237365409
Test progress: https://tokenjunkielabs.slack.com/archives/C0C05UVE0EA/p1788867480195849

## Delivered source and scope

Only new `import_mapper.py`, `test_import_mapper.py`, `IMPORT_MAPPING.md`,
`mapping_examples/stock-export.csv` and `mapping_examples/stock-profile.json`
under `revenue/hive/supplier-reorder-assistant/`, plus this record.
Existing engine, browser, receipt history, backup, workspace CLI and peer tests
are not modified. Explicit profiles map every canonical field to an exact
source header or approved string constant. Missing fields are never assumed.

## Actual cloud-container validation

```
PYTHONWARNINGS=error::ResourceWarning python -B -m unittest -v test_import_mapper test_reorder_assistant test_receipt_history
```

64 tests passed in 7.292 seconds, zero skips: 29 new mapper methods, 9 original
planner methods and 26 receipt-history methods. This uses the complete composed
engine blob `14c4e2a724b07c0104bd64cff24712a014d4234e`, SHA256
`5d2414dee8a480e835633843182a58cd03700745c00948c9c91c1ee05ea51c01`.

Coverage includes all three canonical loaders, real CLI subprocesses, exact
leading-zero IDs, Unicode/BOM/multiline provenance, ambiguous profiles and malformed
CSV, every-record validation beyond the preview, explicit size limits, input and
existing-output preservation, symlinks/hardlinks, and six concurrent output
writers yielding exactly one complete new file. The mapped inputs produce an
unsent nine-unit filter draft totaling 38.25; a four-unit delivery followed by
an identical history replay adds stock once. The documented fictional stock
example matches existing sample stock and retains its review-only alternative.

## Exact published-content identifiers

| New file | Git blob SHA | SHA256 |
| --- | --- | --- |
| import_mapper.py | 493de2a8402278eb0f27d53e58754da2f5366fbb | e3ca6c6d61adc9c0dd7a90db7fdbdbe4afc76d7323dbd052b4fbe08d252b140b |
| test_import_mapper.py | 2d989194a121efa809a4f53043288d77f8997dc5 | 77546065da3a16e995594e1ce9aaa6a69ff464da31385ec18c59ba777abfb649 |
| IMPORT_MAPPING.md | 52e0617c08763ec2c9e820fd09d49172bfb790d1 | 50299a35bfed4206656cf70ac584398157d016971bc69637f711324457787b7c |
| mapping_examples/stock-export.csv | 73cc21012e30a7a7aaebbfaea0354bcda0fedd36 | fa65c75cc3413347e6d966a943ecd1e671cd06d6bf602ed092ac50f9771c6b42 |
| mapping_examples/stock-profile.json | 453e0691addfe3349bb6a714d1fd2f472ead9393 | 9e9751ae7d20652bd0e0ac95d628edeec0099eb1982943b9a9c45feee8ff98be |

Connector-created blobs matched locally tested bytes. The associated PR and
Slack landing reply carry the actual head, merge and readback receipts; this
file records source validation, not a claim of hosted CI success.

## Limits

CSV-to-CSV onboarding only. No inferred SKU mapping, quantity/rule defaults,
currency or unit conversion, supplier send, purchase, customer data, provider
operation, owner-PC work, deployment or paid infrastructure. No repository-wide
CI or customer acceptance claim. Output creation requires a filesystem supporting
hard links; it is not a multi-file transaction or a power-loss durability promise.
