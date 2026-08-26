# White Box archive transfer inventory — LANDED

From: `BRANDED: Dissident - shameful`

Date: 2026-08-26

## Exact implementation

- Integrated current-main commit: `e130c4854ca677ce1204f318f5b7febbff3d608b`
- Expected parent: `6083adf8c063ff81ae82a9dd884e2483ba0591c7`
- `host/whitebox_archive_inventory.py`: blob `ab16d780663b0f823277cdecc4b4c6be557f9efb`
- `revenue/ip/whitebox_archive_inventory.schema.json`: blob `e45fffeae0370ce140ad6df283381141713d4e64`
- `revenue/ip/whitebox_archive_inventory.json`: blob `dfc9923c290837151454b086df1af25aed724330`
- `test_whitebox_archive_inventory.py`: blob `dd824fee9efd6c188b7f331749e7df3cdd74ba52`
- Existing archive payload bytes were read only and were not copied into Commons.

## Measured inventory

- Exact local source class: owner-local `WhiteBox_Research_Archive`; its absolute path is not published in the inventory.
- Files: `7,946/7,946`; directories: `56`; bytes: `16,172,446,060` (`15.062 GiB`).
- Deterministic whole-tree SHA-256: `d67234a1e0d69dba621f4073ecfbaf77db298134d3bd516fba30fc2062467bc9`.
- Eight local model groups exactly match the public `_INDEX.json` after the public `.gguf` identifiers are normalized to archive directory names.
- Public evidence blobs remain `_INDEX.json` `8b352151f13dac000ff9599ef06525b5fe744aa8` and `WhiteBox_Research_Archive_README.md` `ec36adc3fc32d6812fbc85c7598aff748cb0c120`.
- Dominant payloads: `4,914` `.qbin` files / `12,845,769,064` bytes and `2,639` `.f32` files / `3,285,559,912` bytes. Every payload byte is SHA-256-bound in the public manifest.

## Transfer classification

- License: `NOT_LOCATED_REVIEW_REQUIRED`. The exact archive filename census found zero `LICENSE`, `LICENCE`, `COPYING`, or `NOTICE` files.
- Provenance: `PARTIAL_OWNER_LOCAL_PLUS_PUBLIC_INDEX`. The archive READMEs say each `.qbin` copies tensor bytes from its model file, but the archive does not preserve verified source-model download receipts or upstream license records.
- Sensitive-data pattern status: `POTENTIAL_PERSONAL_DATA_REVIEW_REQUIRED`.
- Credential/private-key patterns covered all `393` non-numeric artifacts / `41,117,084` bytes. Personal-data patterns covered all `384` text-like artifacts / `40,630,059` bytes.
- One Windows-user-path pattern occurs in one file: `proof/artifacts/SmolLM2-360M-Instruct-Q8_0-CLEAN__proof_20260802_070633/PROOF.md`. Its matched value is not published.
- The scanner does not claim sensitive-data absence. It publishes no matched value, local absolute source path, or archive payload.
- Archive-license offer ready: `false`; pricing ready: `false`; public sample release cleared: `false`.
- Remaining evidence is exact: upstream/source-model license review, source download provenance, redaction of the one path finding, and sampled manual sensitivity review.

## Verification

- `python -W error -m unittest -v test_whitebox_archive_inventory.py`: `9/9 PASS`.
- Deterministic synthetic rescan covers a chunk-split live-key-shaped fixture without publishing the matched value.
- Draft-2020-12 schema validation passed using the exact current-main Commons `MiniSchemaValidator`.
- CLI validation returned `VALID`, exact counts, exact tree digest, and both uncleared release flags.
- `py_compile`, parent diff check, exact remote blob readback, ancestry, and `open_door_guard.py` passed.
- No existing archive, patent, grants, Outcome Commerce, or TITAN paths were changed. No Cursor was used.

## Owner need

None recorded. The remaining work is evidence collection and redaction, not a question or permission request.
