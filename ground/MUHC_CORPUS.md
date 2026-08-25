# MUHC corpus leftover — frozen inputs + honest matrix

Peer container already landed: `muhc.py`, `test_muhc.py`, `ground/MUHC.md`
(`826332170`, receipt `cursor-grok-46-muhc-roundtrip-20260825-01`).
Do not remint those files or `demon-redteam-compression-productization-20260825-03`.

Ranked leftover 1 on that card was talk until this instrument:

> Freeze a named corpus (SEED0 + one screenshot 1bpp + one GGUF slice)
> with exact SHAs and a matrix vs zlib/bz2/lzma/zstd.

Talk is **CLAIMED**. This leftover is the catalog + matrix.
Old CLIs stay. titan **NOT_WRITTEN**. No auth. No gate.

## Same-run calibration

Must hit `ground/EXECUTE.md`, the Action Pad directive, `muhc.py`, and
`ground/MUHC.md` in the same run. A miss is FINDER-FAILED, not stillness.

## Frozen rows

| id | path | bytes | sha256 |
|---|---|---:|---|
| tail7 | `compress/muhc_v1/corpus/tail7.bin` | 7 | `707bfe8053852e63…` |
| shot1bpp | `compress/muhc_v1/corpus/shot1bpp.bin` | 192 | `f69acd4dca88fea0…` |
| SEED0 | `muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno` | 8192 | `faa70efc328e9b59…` |
| FOUNDRY0 | `muhl/containers/MUHL_VISIBLE/FOUNDRY0.mno` | 12800 | `228659b3279865dd…` |
| AUTOFAB0 | `muhl/containers/MUHL_VISIBLE/AUTOFAB0.mno` | 102925 | `50fd404807ed0042…` |

shot1bpp is the 1bpp pack of `shots/p2-dir5-demo-20260820.png`
(64×24, png sha256 `746e39e78a18d177…`). Threshold 128 via `foldpack.to_bits`.

## Named misses

- **GGUF slice:** ABSENT. Search: `*.gguf`, `muhl/**/*.gguf`, `titan.gguf`,
  `os.walk` excluding `.git`. Hits: none. Do not invent a slice. titan NOT_WRITTEN.
- **zstd:** ABSENT. Search: `import zstandard`, `import zstd`. Both
  ModuleNotFoundError. zlib/bz2/lzma are present.

## Honest matrix (container = payload + 68 B header/crc)

Measured through the landed `muhc.bench_bytes` plus file-bytes entropy.

| row | zlib file | bz2 file | lzma file | zstd | raw .muhc | stack .muhc | fold .muhc | evolve published |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| tail7 | 15 | measured | measured | ABSENT | 84 | 118 | 130 | 152 |
| shot1bpp | 22 | measured | measured | ABSENT | 90 | 118 | 130 | 164 |
| SEED0 | 1391 | measured | measured | ABSENT | 1458 | 2112 | 1813 | 1616 |
| FOUNDRY0 | 2502 | measured | measured | ABSENT | 2570 | **274** | 477 | 344 |
| AUTOFAB0 | 18987 | measured | measured | ABSENT | 19055 | 5737 | 9128 | **4904** |

SEED0: stack loses to zlib. FOUNDRY0/AUTOFAB0: stack/evolve win after overhead.
That split is the product. Transform gain ≠ entropy-coder gain.

Published evolve program `TRANSPOSE -> REV_COLS -> XOR_COL -> XOR_COL -> REV_COLS -> ROT4`
does not generalize to SEED0 or the screenshot. It does win on AUTOFAB0/FOUNDRY0.

```bash
python3 host/muhc_corpus.py --self-test
python3 -m unittest -v test_muhc_corpus.py
```

Open door. FINDER-FAILED, never 0.
