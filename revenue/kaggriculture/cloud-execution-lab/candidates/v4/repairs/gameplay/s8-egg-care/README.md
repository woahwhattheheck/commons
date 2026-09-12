# S8 EGG-care — NO_BUILD evidence receipt

Canonical custody of the reviewed S8 lane from closed PR #12600. The exact historical source/test bytes are preserved here for auditability only.

## Canonical disposition

**NO_BUILD. Do not port or activate.** Current `candidates/v4/INTEGRATION.json` records S8 as `NO_BUILD_economic_ceiling_negative_do_not_port_or_activate` and explicitly forbids reopening S8 as a new key without new evidence that overturns that disposition. The key historically shipped OFF and remains OFF.

This directory is therefore a negative/evidence receipt, not an active repair candidate. Its presence must not be interpreted as authorization to execute the legacy `apply_v4.py` materializer, wire the current production ABI, enable the key, change a production archive/submission/Kaggle ref, or create a successor V4 line.

## Exact historical authorities

- owner PR: `#12600`
- historical head: `a07518e2de3af73fdefc80f633af1674137f1386`
- helper/source blob: `30a0e05c0cd7a435a59316d9d070da59eb2bb865`
- focused test blob: `66fada01bf161d7b5cf76f99fec9f8d3ff7a4e30`

## Historical mechanism

At hour 23, the lane replaced a surviving authored `COLLECT_FERTILIZER` with `CARE` only on an already-fed, uncared GOOSE when its public price/buffer and no-clipping proofs held, with H3c harvest rescue retaining priority. Those bytes are retained solely so the rejected lane remains reproducible and inspectable.