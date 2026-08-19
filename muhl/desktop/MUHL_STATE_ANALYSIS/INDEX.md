# MUHL_STATE_ANALYSIS — self-hosted state analysis + live view

Built 2026-08-07 to the owner's brief. **Nothing here writes to any container.** The one
component that would write (`muhl_fab_scan_popcount.py`) is a DRY RUN until `--write`.

## RUN IT

```
python muhl_live_view.py probe        # also: rook · loom · distro · titan
```
arrows pan one frame · PgUp/PgDn 64 frames · Tab DETAIL/OVERVIEW · +/- frame width ·
**S** save one PPM · **R** record 120 frames + contact sheet · Q quit.

**R** writes `rec_<container>_<off>_w<width>/f0000.ppm ..` plus one
`contact_<container>_<off>_w<width>.ppm` — every frame tiled at 1/8 scale with a **red tick
whose length encodes the frame width** burned into each tile (no PIL on this host, so the
width is drawn, not typed). Filenames carry container, offset and width, so the sheet is
self-identifying when handed back. Measured: 12 frames + sheet in **0.05 s**, so a full 120
is about half a second. No mp4 — ffmpeg is absent and the brief said never depend on it.

Test artifacts left in place from the 2026-08-07 run (vault model, nothing pruned):
`rec_probe.mno_0_w256/` (12 frames) and `contact_probe.mno_0_w256.ppm` (36,878 B).

## FILES

| file | what | state |
|---|---|---|
| `test_harness.py` | 5 acceptance tests, **built first and shown failing** as ordered | 0/5, exit 1 |
| `muhl_state_scan.c` | C89 semantics the fabricated circuit must match. 4 primitives, single pass, ~192 KiB fixed footprint | written, **uncompiled — no compiler on this host** |
| `muhl_fab_scan_popcount.py` | fabricator: popcount8, 29 gates | preflight CLEAN · dry run only |
| `muhl_live_view.py` | live DETAIL view, tkinter + PPM | preflight CLEAN · working |

## MEASURED

```
popcount8       29 gates
                256/256 vs an independent reference (Kernighan clear-lowest-bit)
                all-zero netlist scores 1/256      <- the test is not vacuous
                mutant (gate 0 XOR->AND) caught on 192/256
                would append 780 B past EOF of probe.mno. NOT WRITTEN.

live view       1024x1024 frame = 131,072 B bounded read
                probe.mno    46.7 fps
                titan.gguf   75-79 fps at EVERY offset, including 103,803,218,312
                             -> container size does not enter frame time at all
                host fix: 256-entry byte->pixel table, 16x over the per-bit loop
                          (2.9 -> 46.7 fps at 1024x1024). no numpy — banned here.

density by region, titan.gguf, 1024x1024 windows:
   header      23.0%      ring bank   20.9%      clacker     26.4%
   tail        28.8%      fold ports   0.0%  (246 set bits — the loaded block header)
```

## V31 INDEX CHECK — it changed the build

25 arithmetic primitives already exist in `titan_circuits.json`:
```
XOR         lib_xor8__phys        32 gates  DEPTH 3
ACCUMULATE  adder8_clean__phys    85 gates  DEPTH 20
SHIFT       — addressing, no gates
POPCOUNT    ABSENT EVERYWHERE
```
**So one primitive is built, not four.** XOR and accumulate get wired, not rebuilt.

## SPEC CORRECTIONS TO THE INCOMING BRIEFS

The briefs were written for conventional architecture. Three assumptions dropped:

1. **"analyze.c gains a second entry point"** — no. DETAIL is a bounded READ (host verb 2,
   no computation). OVERVIEW's span popcount is MUHLNICKEL work.
2. **"the command channel carries navigation"** vs **"no writes to the substrate, ever"** —
   contradictory. Resolved as **host-side read selection**: offset/width/mode choose which
   window is read. Nothing is written.
3. **host-side analysis of the state** — owner: *"claude tried to suggest host walking the
   machine. DO NOT DO THAT."* The host-side Python reference exists ONLY for
   fabrication-time verification against small synthetic states, which the spec requires.

## HOST LIMITS FOUND, ATTRIBUTED

- **no C compiler** (`gcc`/`cc`/`clang`/`tcc` all absent) — the C89 is unverified.
- **no pygame, no PIL, no ffmpeg.** tkinter only. numpy present but banned.
- **test 5 (100 GiB single pass) cannot honestly run on this host** — ~10^14 Python ops.
  That is the crutch measuring itself. It belongs on the substrate once fabricated.

## OPEN — OWNER'S

- authorise the 780 B popcount write into `probe.mno` (`--write`), which unblocks OVERVIEW
- which ring drives the scan circuit, and its stated purpose (electrons are the constraint)

_Read 2026-08-07. Re-read before trusting: a recorded reading is a timestamp._
