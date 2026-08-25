# SUBZERO EXPLORER v2 — deterministic validation, not a runtime claim

This is the non-duplicative validation layer over the existing Subzero
inventory (`ground/SUBZERO_TECH.md`), buyer packet
(`revenue/subzero_buyers/pack.json`), and public archetype tree. It does not
remint those catalogs. It binds each checked-in `.mno` excerpt to exact source,
structural test, card, sidecar, packet, hashes, and commit-pinned links.

The instrument is synthetic and repository-only. It does not open, infer from,
or mutate a live Titan, host, device, model, or container.

## Evidence contract

The catalog uses exactly four exclusive classes:

- `STRUCTURAL_ONLY`: artifact SHA-256 and stored header match the checked-in
  packet, and the named fabricator, structural test, and sidecar are present in
  the calibrated public-tree search space. Git copies do not run.
- `RUNTIME_MEASURED`: structural evidence plus a bound receipt with a PASS
  runtime measurement, runner/test/input/output hashes, process/run ids, and a
  timestamp. Presence of Titan, a path, or a file never counts.
- `CUSTOMER_READY`: structural evidence plus a bound delivery and buyer PASS
  receipt whose acceptance checks include the artifact SHA-256. Payment alone
  never counts.
- `UNKNOWN`: calibration, hash, header, source, test, sidecar, or receipt
  binding failed. Every miss names the explicit search space; a miss is not a
  global absence claim.

The legacy source token `CROSS_PROCESS/RUNTIME_MEASURED` normalizes only to the
public v2 token `RUNTIME_MEASURED`; the raw token remains source context, not an
extra class.

## Deterministic packet

`ground/SUBZERO_EXPLORER.json` records `source_commit`, `source_tree`, the
calibrated path set, SHA-256 and Git blob SHA-1 for every source, and URLs pinned
to that exact commit. It contains no timestamp, machine name, or host-derived
fact, so the same inputs produce byte-identical sorted UTF-8 JSON with LF line
endings.

The generator is `host/subzero_explorer.py`:

```bash
python3 host/subzero_explorer.py --self-test
python3 host/subzero_explorer.py
python3 host/subzero_explorer.py --root . \
  --source-commit <40-hex-commit> --source-tree <40-hex-tree> \
  --write-catalog ground/SUBZERO_EXPLORER.json
python3 -m unittest -v test_subzero_explorer.py
```

The default command verifies that the checked-in catalog is exactly what the
generator produces. Writing requires explicit Git objects; it never guesses a
host or substrate.

## Buyer acceptance receipt

`revenue/subzero_buyers/validation_receipt.schema.json` defines one strict,
public receipt. The explorer can download a measured/PENDING template for any
artifact. A buyer may return a PASS receipt bound to the source commit/tree and
artifact hash. Runtime and buyer acceptance are separate schema sections.

Offers remain referenced, not copied: P01 catalog/receipt, P03 measurement
harness, and P05 failure packet in `revenue/subzero_buyers/pack.json`.

No auth. No gate. Possessing the link is sufficient access. The explorer has no
admission form, account distinction, or action tier. Receipt download and
posting are not conditioned on identity.

Slack `1787646413.997539`; handoff
`jojo-model-work-profitability-bridge-20260825-01`. Talk is not a land.
FINDER_FAILED / FINDER_UNVERIFIED, never an uncalibrated zero.

V2 follow-up `jojo-subzero-explorer-v2-followup-20260825-01`, Slack
`1787647728.185449`, remains as compatibility metadata in the catalog's `v2`
object; the detailed proof now lives on each artifact row.
