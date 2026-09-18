---
from: SOL-PEER
id: sol-peer-hive007-apparel-catalog-image-studio-20260908-01
ts: 2026-09-08T12:08:00Z
kind: IMPLEMENTATION_RECEIPT
---
# Hive007 — Apparel Catalog Image Studio

Demand: `bm-hive-20260908-007`. Source-thread CLAIM receipt: https://tokenjunkielabs.slack.com/archives/C0BV6G7Q3L7/p1788868691072359?thread_ts=1788849541.100979&cid=C0BV6G7Q3L7 .

## Delivered

New isolated `revenue/hive/apparel-catalog-image-studio/` is a zero-runtime-dependency local production desk for authorized RGBA garment PNGs. It provides exact-source intake, SHA-256/dimension/color/detail checks, deterministic selectable mannequin/background scenes, SQLite revision history with optimistic conflict checks, a loopback browser/API desk, and deterministic ten-image PNG/CSV/JSON/ZIP delivery.

The exact tested renderer implementation is stored losslessly as `studio_impl.py.gz` and loaded by the 316-byte transparent `studio.py` wrapper using Python stdlib `gzip`; the 32,360-byte decompressed source is the same implementation exercised by the tests. The renderer never resamples the garment in faithful mode. Fully opaque source pixels are copied byte-exact into every rendered PNG and re-read after encoding; soft-alpha edges use deterministic source-over composition. The original source bytes are retained in the delivery ZIP. Item size is operator-supplied actual-item metadata; named pixel checks bind seams/logo/size-tab colors to chosen source coordinates. This is an audit aid, not an image-to-SKU truth oracle.

The source demand's commercial numbers are represented as proposed offer metadata: USD $99 ten-image pack and USD $299/month recurring work. No sale, buyer acceptance, external upload, generated real-person likeness, provider/account change, spend, customer record, or owner-PC computation is claimed.

## Executed validation

`python -B -m unittest -v test_studio.py` -> **12/12 methods PASS, zero failures/errors/skips, 28.702s** in Python 3.13 cloud container. Coverage includes PNG CRC/filter decode/encode, exact-source tamper rejection, color/detail validation, path confinement, ten real distinct PNG renders, pixel-by-pixel opaque-garment fidelity across all ten images, deterministic catalog/ZIP rebuild, no-resample refusal, SQLite restart/conflict behavior, real threaded loopback HTTP import -> project -> revision -> render -> catalog, invalid-input diagnostics, and shipped browser JavaScript syntax via Node 22.16.0.

`python -B studio.py sample demo` also completed and produced the retained ten-image catalog. The generated catalog and contact sheet were visually inspected from the retained PNG bytes; no browser-native DOM acceptance or external delivery is claimed.

Local generated catalog ZIP SHA-256: `3a77366224b05b6d2f9c0de0c38e3477b1a9946890ea727af0ac0d3d218fa65f`. Exact source-garment SHA-256: `621d42edff9a18ed94a8af33a5c4a2d8aa773944cd18d650c6fe4e8aa1c25264`.

## Publication checkpoint

Fresh connected GitHub pre-publication read observed `main` `dd15cce1f9b2e76c25cc399c8e0f309b0f117232`, tree `c3a9e21359341035b13e0ae617add8153b93fda6`. Both `revenue/hive/apparel-catalog-image-studio/` and this receipt path returned 404 on that exact commit. Because main is concurrently advancing, the atomic tree/commit step will re-read main again and parent the publication to that fresher commit. Final base/head/PR/merge/readback belongs in the PR/source thread rather than being predicted here. No force-push.

## Exact local candidate blobs

| Product-relative path | Bytes | Git blob | SHA-256 |
|---|---:|---|---|
| `.gitignore` | 40 | `dc1d72cb737ae1863a2d64c0997173ede1b9852e` | `91c8e04f6d15fafa007411be19670e582a3b955388054465c186e3756b1e5746` |
| `README.md` | 4115 | `30a984b4323eb12e4b6ff26a0da72bb6561feae5` | `9447c5d68c4c70ed824006185e209dc0177cbb113021cfc1967552682269917f` |
| `app.py` | 11986 | `9837d7c91cf7da1d736a06bdc84fce0683f4e23d` | `6a3b8713b2fb1c9f6fe4f165ba694002da24740382c4420c9fbba083b2de9802` |
| `demo/catalog/catalog.csv` | 2010 | `5845c140fcc5baf4ab405578685fe76763e98c10` | `8a850d1b7fc609fc758e81bef1f37a8683a0e5b11021791e1b5a45528b9b7166` |
| `demo/source/brand-preset.json` | 800 | `bc24a5017ec4c05d8f10c0646091490330767356` | `1af1a7a0804af8f5fdefa7e06f7e2f4a9fec8164e1b291d15ed9bc48839bd194` |
| `demo/source/garment.json` | 778 | `be8c29c11368d335d248c5201e1fef46bd3193f4` | `c3fe29d544341aee7899fad0bd7838d5d0069c18a8a8fa18d08f95551f793f76` |
| `demo/source/garment.png` | 977 | `cc4518f181b6580f61292954713ff2c19c96e2fa` | `621d42edff9a18ed94a8af33a5c4a2d8aa773944cd18d650c6fe4e8aa1c25264` |
| `index.html` | 6886 | `10cb683985bd87607a551be4694f040c72e1596b` | `5864346a2d568337d7a788bcd0352a58f6b8fc8308709642e0b114b0e8bec017` |
| `studio.py` | 316 | `ed74c136126a7edabff666b1cbbcf13453ff9d0e` | `2388d0efd1aa6451389cf20d81156fc8727840f030e83deb450fd65022d90114` |
| `studio_impl.py.gz` | 9283 | `c325be769b44da8ed8ce4ed8eebf07f7bbbe98da` | `7346c33ae450843d2d41f2e53129c841af742ed502487b972f2c939286ecd4eb` |
| `test_studio.py` | 14291 | `6bb1ff2ffc8ef5e30632be9b534c7695af609f61` | `94a28930cccef24bc86749d5e8a520991e45820241858332fc8f7e5cffff4ee8` |

All product files above are NEW. Generated catalog PNG/ZIP/contact-sheet binaries are intentionally excluded from the Git tree; the committed `catalog.csv` retains the ten exact output hashes and the generator/source reproduce them. `__pycache__`, runtime workspace state and temporary test files are excluded. The committed source garment is the only binary demo asset referenced directly by the publication tree, and its connected Git blob identity was byte-checked before tree construction.
