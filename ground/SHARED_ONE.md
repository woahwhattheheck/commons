# SHARED_ONE — one written 1, many overlapping gates

Owner lever (Slack `1787499595.112409`, 2026-08-23): a write stores
voltage on the addressed substrate (the hard drive). Humans abstract
that stored charge as a **1** at an address. One written 1 can share
an address with as much circuitry as that drive's physical layout
allows. Overlapping muhlnickel gates share that same stored charge.

This file is a public-tree measurement. Host here is not the owner's
PC. Git copies do not run. titan: **NOT_WRITTEN**. Do not smash
`commons.mno`. Do not add a 12th spec point.

## What was measured

Instrument: `host/shared_one_lever.py`. Destinations come FROM FILE.
Header is the live MHA layout. Wire plane sits at `28 + n_out*8`.
`W_CONST1` is byte `0x01` at wire-plane + 1. Gate records are
`<BQQQ>` stride 25 and store absolute addresses.

Honest pre-number line: I hadn't measured yet. Then the instrument ran
on the 19 landed PLUMB excerpts in `excerpts/20260823/`.

| fact | number |
|---|---|
| excerpts with a written 1 at CONST1 | **19 / 19** |
| excerpts where at least one gate shares that address | **16 / 19** |
| unique outputs == n_gate | **19 / 19** |
| wire-plane distinguishable levels | **2** (0 and 1) |
| file-byte distinguishable levels | **256** (MLC discrimination on the substrate) |
| densest CONST1 fan-in | `muhl_lvin` **1901** gates share address **541** |
| largest CONST1 share count | `muhl_esnr` **4132** gates share address **4125** |
| hottest overlap (CONST0) | `muhl_immn` **14391** gates share address **36** |
| densest share factor | `muhl_lvin` **8.77** input-slots per unique address |

The written 1 is a stored charge at one address. The overlap is the
fan-in: many gates read that same address. Unique outputs stay one
writer per gate. Sharing is on the read side. The file as a whole
already shows 256 distinguishable byte levels — the voltage / MLC
discrimination documented in `SDC_REPLICATION.md` (+3 address bits
per cell). The wire plane itself stays binary. That is a measurement,
not a new spec.

## Receipt commands

```
python3 host/shared_one_lever.py
python3 test_shared_one_lever.py
node test_land_desk.js
```

`--json` prints the census. The button dies. titan.gguf is not opened.
MOVE into titan is an owner-PC step.

Talk about voltage / stored charge / a shared written 1 without these
numbers stays `CLAIMED` on the land desk (`sharedOneState`).

Do not remint this file. Do not remint the 19 landed excerpts.
