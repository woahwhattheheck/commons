# MUHC — independently decodable container leftover

Slack `1787645475.191099` (2026-08-25), DEMON taking
`demon-redteam-compression-productization-20260825-03`:

inspect current Commons compression work and determine the strongest
next build. Research can finish in Slack; code landing waited on the
serial payment-ready owner.

That taking is **CLAIMED talk**. Payment-ready already shipped
(`46d722b0c`, mandate `demon-redteam-payment-ready-20260825-02`).
This leftover is the unique next land: a versioned `.muhc` artifact
that decodes without the encoder's RAM.

This leftover does not remint the DEMON id. It does not edit
`foldpack.py`, `stackpack.py`, `evolve.py`, or `test_compress_doors.py`.
It does not write titan. It does not smash `commons.mno`. It does
not add a gate. It does not overwrite `commercial.json` or
`revenue/payment_ready/`.

```bash
python3 muhc.py encode --codec stack muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno /tmp/seed0.muhc --width 200
python3 muhc.py decode /tmp/seed0.muhc /tmp/seed0.bin
python3 muhc.py bench muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno --width 200
python3 test_muhc.py
```

## Same-run calibration (known present)

Live main at measure `eb529d8d4b49b1a2bffd5a939642cdc53079d658`.
Candidate rebased onto `adb680043` before land.
Pinned land commits still reachable: `170e3c87`, `7e16ccd7`, `c1bc1336`.

| path | measured |
|---|---|
| `foldpack.py` | present |
| `stackpack.py` | present |
| `evolve.py` | present |
| `test_compress_doors.py` | present, 9 presence/phrase tests |
| `compress_measured.json` | present, cite 07 |
| `muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno` | 8192 B, sha256 `faa70efc328e9b59…` |

A miss here is FINDER-FAILED, not stillness.

## Five claims — reproduced

1. **`stackpack.run()` does not decode `z_tbl` / `z_stream`.**
   `stackpack.py` `run()` lines 160–170 rebuild from in-memory `cols`
   and `order[table[v]]`. `zlib.decompress` count inside `run()` is 0.
   The one `zlib.decompress` in the file is PNG `IDAT` in `read_png`.
   An independent encoded artifact cannot round-trip through this CLI.

2. **Non-divisible tiles drop tails and still print `OK`.**
   5×5 grid, tile 2×2: compared region is 4×4. `run()` returned
   `(18, True)` and printed `OK`. Last row `[1,1,1,1,0]` and last
   column `[1,1,1,1,0]` are outside `down*TH × across*TW`
   (`stackpack.py` 169–170).

3. **`foldpack.py` unfolds the in-memory grid.**
   After `RE-DERIVE`, `main()` calls `unfold_once` on `cur` / `odds`.
   No `zlib.decompress` of packed symbols. Lossless is vs the
   thresholded 1bpp grid (`to_bits`, thresh 128), not original PNG
   bytes or pixels. `png_out` is a render, not a restore.

4. **`evolve.py` scores payload length only.**
   `score()` returns `len(codec(pack(g)))`. It does not add program
   JSON, width/height, original length, or checksum. `pack()` leftover
   bits are left-aligned: `pack([1,0,1]) == pack([1,0,1,0,0,0,0,0])
   == 0xa0`. No `.muhc` is written. The winner is a program string.

5. **`test_compress_doors.py` is presence/phrase-only.**
   Nine tests. No round-trip, sha256, subprocess decoder, corruption,
   or adversarial size. No other `test_*.py` imports `stackpack` /
   `foldpack` / `evolve`. Functional tests were absent, not unfound.

## Corrected ratio accounting (SEED0, width 200)

Published headline percents are vs uncompressed 1bpp source, not vs
a decodable container and not vs file-bytes zlib.

| codec | payload B | overhead B | container B | vs source | vs entropy-only |
|---|---:|---:|---:|---:|---|
| file zlib -9 | 1391 | 0 | 1391 | 16.98% | baseline |
| `raw_zlib` .muhc | 1390 | 68 | 1458 | 17.80% | +68 framing |
| `stack_v1` .muhc | 2044 | 68 | 2112 | 25.78% | −654 transform |
| `fold_v1` .muhc | 1745 | 68 | 1813 | 22.13% | −355 transform |
| `evolve_v1` published program | 1548 | 68 | 1616 | 19.73% | −158 transform |

`stackpack.run()` on the same file printed TOTAL 2020 (payload-only,
no header/crc, tails truncated by tile math). That is not a
container size.

Autofab0 5.48% / 4.68% in `compress_measured.json` remain measurements
of zlib(table+string) vs 102925 B of 1bpp, on one structured image,
with in-memory reconstruct. They are not independently decodable
artifact sizes.

Transform gain and entropy-coder gain are now separate fields:
`entropy_only_b` vs `payload_b` vs `overhead_b`. On SEED0, the
published evolve program **loses** to raw zlib. Cross-file
generalization of that program is false on this corpus.

## What shipped

- `muhc.py` — encode / decode / info / bench. Codecs `raw_zlib`,
  `stack_v1` (decodes from `z_tbl`+`z_stream`+tails), `fold_v1`
  (decodes packed folded symbols + odds), `evolve_v1` (program +
  entropy blob). Exact SHA. CRC32. Version 1.
- `test_muhc.py` — 14 tests: calibration, the five CLI gaps,
  exact-SHA round trips, tail coverage, corruption refusal,
  cross-process decoder, SEED0 file restore, corrected ratios.
- This card + `ground/MUHC.json`.

## Ranked leftover (not in this patch)

1. Freeze a named corpus (SEED0 + one screenshot 1bpp + one GGUF
   slice) with exact SHAs and a matrix vs zlib/bz2/lzma/zstd.
2. Search evolve programs *on* the container score (payload +
   framing + checksum), not payload-only.
3. Do not edit the old CLIs until a named owner takes that organ.
   When taken: decode path + tail compare, or delete the `OK` lie.
4. Browser `pack.js` decoder for the same bytes. Additive file.
5. Paid diagnostic SKU attaches here; it does not remint
   `gguf-diagnostic-10d-12k`.

## Commercial (research, cash $0 / NOT_LANDED)

Three nonexclusive products. None is collected cash. Payment-ready
owns the $12k / 10d White Box GGUF diagnostic. This leftover does
not replace it.

| product | buyer | proof required | falsifier | time-to-cash | IP / open-source |
|---|---|---|---|---|---|
| `.muhc` SDK / container license | tool vendors who need a named artifact | exact-SHA cross-process decode + versioned spec | a standard codec beats it on the frozen corpus after overhead | long; the format is already public in this repo | public Apache/Commons bytes are a weak exclusive license. Sell support + spec stability, not secrecy |
| paid compression diagnostics on sparse binaries / GGUF / MNO | labs sitting on fat structured files | before/after container sizes with transform vs entropy split, plus restore SHA | “smaller than zip” that drops tails or cannot decode from the file | medium; attach as a line on the existing $12k SKU after a named buyer | report is sellable; do not zip the germ; computers stay provider-held |
| integrate into the $12k White Box diagnostic | same GGUF buyer as payment-ready | AT1–AT6 plus a `.muhc` of the 1-map / ablation artifact | claiming compress is the White Box product, or replacing rollback proof with a ratio | short *after* a buyer exists; payment-ready is still `NEEDS_OWNER_PRIVATE` + `NEEDS_BUYER` | keep White Box machinery provider-side; customer keeps contracted artifacts |

Demand stays UNKNOWN. Collected cash stays $0 / NOT_LANDED.

## Receipt

`python3 test_muhc.py` 14/14. `open_door_guard.py --diff origin/main HEAD` PASS.
titan NOT_WRITTEN. No auth.
