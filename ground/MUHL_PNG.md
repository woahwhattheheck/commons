# MUHL_PNG — surface bytes as pixels and as numbers

`muhl_png.py` at repo root. Read a file, emit one artifact, die.
Nothing is mutated. Every source is opened `'rb'` and never written.

**Pure stdlib: `zlib` + `struct` + `math`. No numpy. No Pillow. No third-party anything.**

That constraint is the whole point. numpy is out of spec in the runtime path and Pillow is not
installed, so every "just use a library" answer was closed. It was never needed.

---

## Why no library is required

A PNG is four chunks and a zlib stream. That is the entire format:

```
89 50 4E 47 0D 0A 1A 0A          magic
IHDR    width, height, bitdepth=8, colortype (0=gray, 2=RGB), 0, 0, 0
IDAT    zlib.compress( each row prefixed with one filter byte 0x00 )
IEND    empty
```

Every chunk is `>I length | 4-byte tag | data | >I crc32(tag+data)`.

The writer is ~14 lines at the top of the file. That is all of it. If you can call
`zlib.compress` and `struct.pack` you can already write PNGs, and both are in the standard
library of the Python that is already on the machine.

---

## The record-alignment trick

`--width 200` is the flag to remember.

**200 bits = 25 bytes = exactly one `<BQQQ>` gate record per scanline.**

Render a `.mno` at `--width 200` and every horizontal line of the image is one gate. The
vertical bands you see are the fields landing at fixed bit columns, little-endian, low byte
first:

| field | bit columns |
|---|---|
| `op`  | 0 – 7 |
| `a`   | 8 – 71 |
| `b`   | 72 – 135 |
| `out` | 136 – 199 |

The wide black gutters are unused high bits. In AUTOFAB0.mno the largest value in any field is
8,388,791 — **24 bits used of 64** — so forty bits per field sit at zero and render black. The
image is showing the headroom.

---

## Modes

### Render

| command | what it does |
|---|---|
| `bits FILE OUT.png` | one pixel per **bit**. white = 1, black = 0. |
| `bytes FILE OUT.png` | one pixel per **byte**, grayscale. the byte value *is* the grey level. |
| `rgb FILE OUT.png` | three bytes per pixel, raw triples, no interpretation. |
| `ppm IN.ppm OUT.png` | P6 netpbm → png. renders what the existing probes already emit. |
| `sheet DIR OUT.png` | every `*.ppm` in DIR as one contact sheet. |
| `delta DIR` | frame-to-frame pixel delta across a `*.ppm` sequence. |

### Measure

| command | what it does |
|---|---|
| `stats FILE` | ones%, entropy, zlib ratio, byte histogram, zero-run lengths, stride check. |
| `cols FILE` | per-bit-column occupancy at `--stride`. **which bit positions are ever live.** |
| `fields FILE` | unpack `<BQQQ>`: op census, per-field range and bits-used, **collision count**. |
| `diff A B OUT.png` | XOR two files, render **only the bits that differ**. |
| `heat FILE OUT.png` | ones-density per record as a colour ramp. |
| `hist FILE OUT.png` | byte-value histogram as an image. |

### Survey

| command | what it does |
|---|---|
| `magic FILE` | scan for ASCII magic words, report byte offset + record index. Also lists discovered `A-Z0-9_` runs the known list doesn't cover. |
| `strip FILE OUT.png` | whole-file ones-density overview, read in chunks. Survives a 2 GB container without building a 2 GB image. |
| `entropy FILE OUT.png` | sliding-window entropy as a colour strip. `--window N`. Header, netlist and dead space read as different bands. |
| `records FILE` | text dump of `<BQQQ>` records with raw hex. `--skip N --count N`. |

### Flags

```
--width N    pixels per row (default 256). 200 = one 25-byte record per row.
--scale N    nearest-neighbour magnify (default 1). no resampling, ever.
--offset N   start byte.
--len N      byte count. window a 2 GB file without building a 2 GB image.
--stride N   record size in bytes (default 25).
--cols N     contact-sheet columns (default 4).   --gutter N (default 4).
```

`--offset` / `--len` are how you look at `muhlnickel_dc.mno` (2,147,548,550 B) without
loading it whole.

---

## `diff` is the observability mode

`FILES_CHANGE_UNDER_YOU.txt` says the file changes under you rapidly and that the change **is**
the compute. Until now that was a thing you could assert but not watch.

```
cp live.mno t0.mno            # snapshot
# ... wait ...
python muhl_png.py diff t0.mno live.mno moved.png --width 200 --scale 2
```

Output is a bit count, a byte count, a size delta, and an image in which **a white pixel is a
bit that changed**. At `--width 200` each row is one record, so the image tells you *which
gates* moved, not just how many bits did.

This does not read a viewer, a poller, or Task Manager. It reads the file twice and subtracts.

---

## Receipts measured when this tool was written (2026-08-20)

Run on the copies in `muhl/containers/MUHL_VISIBLE/` at HEAD.

**Documentation check — `CLAUDE_FAILURE_MODES.md` §1 against the bytes:**

```
§1 states, AUTOFAB0.mno byte 0:   op=00000011 XOR  a=143  b=141  out=193
measured:                          op=00000011      a=143  b=141  out=193
                                                                    MATCH
```

**AUTOFAB0.mno** — 102,925 B / 25 = 4,117 records

```
ones            65,299  (7.9304%)
entropy         2.3842 bits/byte
zlib ratio      0.1845
0x00 bytes      77,074  (74.88%)
zero runs       14,191   longest 16 B

op census       op=00000001  1,979  48.07%
                op=00000010  1,033  25.09%
                op=00000100    765  18.58%
                op=00000011    340   8.26%

a    max 8,388,791   distinct 1,506   24 bits used of 64
b    max   524,431   distinct 2,154   20 bits used of 64
out  max 8,388,791   distinct 3,402   24 bits used of 64

COLLISION
   distinct out addresses          3,402
   distinct input addresses        3,276
   addresses that are both         3,275
   input slots landing on an out   8,231 of 8,234   (99.96%)
   REC n out == REC n+1 a or b     1,227 of 4,116   (29.81%)
```

Three input slots out of 8,234 reference an address that is not an `out` somewhere in the same
file. One distinct address.

**FOUNDRY0.mno** — 12,800 B / 25 = 512 records

```
bit columns ever set    29 of 200
bit columns always 0   171
```

**`rec_probe.mno_0_w256`** — 12 frames, 256×256, frame-to-frame pixel delta:

```
12.37  11.15  11.11  11.27  11.91  11.96  11.95  11.69  12.90  13.08  13.49   (%)
```

Monotonic rise across the last three transitions. Frame 0 is columnar; column structure is
present in roughly the top sixth of frame 1 and absent from frame 2 on.

**Container census** — swept across every `.mno` in the repo at HEAD.

> **Corrected 2026-08-20.** The first version of this section said "gate-first 65 / magic-first
> 58". That was a heuristic (`first 4 bytes printable`) reported as a fact, and it silently
> excluded 59 files from the parse entirely. Numbers below say what was actually measured and
> what was not. See `cairn-magic-scan-coverage-correction-20260820-02`.

```
123 containers                              130,219,399 B total
size            min 96 B   median 27,600 B   max 28,870,992 B

contains >=1 of the 15 known magic strings        28
contains NONE of those 15                         95   <- "not these 15", NOT "no magic"

contains any printable ASCII run >=4 chars        58
contains no such run anywhere                     65

length divisible by 25                            64
length NOT divisible by 25                        59   <- stride unknown, NOT PARSED

of the 64 divisible, parsed as <BQQQ>@25
   plausible   (<5% of fields using >40 bits)     63
   implausible (>5%)                               1
```

**59 of 123 containers were not parsed at all.** A plausible parse is consistent with the
assumed layout; it is not proof of it.

Magic words present, with the five that are **not** named in `CLAUDE_FAILURE_MODES.md`
marked — these were found by the sweep, not read out of a doc:

| magic | where |
|---|---|
| `MUHLPKG1` * | all of `MUHLNICKEL_DISTRO` incl. `muhlnickel.mno` 136,450 B and every `SEED0*` / slot |
| `LOOMPKG1` * | `MUHLNICKEL_LOOM_fixed/loom.mno`, `MUHLNICKEL_LOOM_v1/loom.mno`, both 140,454 B |
| `PROBEMN1` * | `MUHLNICKEL_PROBE/probe.mno` 215,317 B |
| `ROOKERY0` * | `MUHLNICKEL_ROOKERY/ROOKERY0.mno` 586,918 B |
| `COMMON1` *  | `MUHL_COMMONS/commons.mno` 17,683 B |
| `TABLEML1`   | `MUHL_COMMONS/table_mail.mno` 17,683 B — magic appears twice |
| `GGUF` `TITANCIR` `MUHLFLD1` `NRING2M1` `MUHLWBX1` | all five inside `READER1.table.mno`, **96 bytes total** |

`AUTOFAB0.mno` returns none of the 15 known strings and **no printable ASCII run of 3+
characters anywhere in 102,925 bytes** (95.92% of its bytes are non-printable). That is
consistent with what §1 says — *"none — byte 0 is a gate"* — and its first sixteen bytes read
`03 8f 00 00 00 00 00 00 00 8d 00 00 00 00 00 00`, which unpacks as `op=3 a=143 b=141`. The
head dump is the evidence; the scan result only bounds what else might be there.

---

## A zero result must carry its own search space

The first `magic` implementation searched a fixed list, then fell back to "runs of 6+ chars from
`A-Z0-9_`", and printed *"none present"*. Three things were wrong with that:

- **It could not find `GGUF`.** Four characters. The discovery pass required six, so the one
  magic most certain to exist in this world was structurally invisible to it.
- Lowercase, mixed-case, non-ASCII, byte-swapped, or internally-split magics: all silently zero.
- *"none present"* reads as **there is nothing**. It meant **I looked for these fifteen things**.

This is the same failure the board already has a law for. A bake reported as the board. A stale
`NOT BUILT`. "The road is blocked" when the truth was "my harness does not show me errors."

So every zero this tool prints now arrives with the boundary of the search that produced it,
and `magic` dumps the first 64 bytes verbatim before any heuristic runs, so a human can read the
header directly instead of trusting a classifier.

`fields` got the same treatment. It will happily unpack **any** file as `<BQQQ>` and print
authoritative-looking numbers, so it now states its assumption, warns when the length is not
divisible by the stride, and runs a plausibility check. Pointed at this very markdown file it
reports **100.00% of fields using >40 bits — HIGH — artefact of a bad parse**. Pointed at
`AUTOFAB0.mno`, **0.00%**. It still says *"a clean-looking parse is not evidence the format is
right."*

The 53 `MUHL_READERS/R_t*_g4_*.mno` all open `03 00 00 00 00 00 00 00` and size scales linearly
in `c`: at `t2_g4`, c2/c4/c8/c16/c32/c64 = 1,800 / 3,600 / 7,200 / 14,400 / 28,800 / 57,600 B —
900 B per unit of `c`. At `t16_g4`: 7,400 / 14,800 / 29,600 / 59,200 — 3,700 B per unit.

These are numbers, not readings. What they mean is the owner's ruling.

---

## Additive law

**v2 added modes. v2 removed nothing.** Every v1 mode produces byte-identical output to before —
regression-checked against the earlier renders when v2 landed. Old tools stay. They are data
points.

Anything added later must keep that property: new mode, new flag, never a changed or deleted
one.

---

## Not this

- Does not write, mmap, fire, or `--go` anything.
- Does not start a server, a poller, or a CUT port.
- Does not interpret the architecture. It reports bytes and arithmetic over bytes.
- `HTTP is not the computer.` This is a surface, and it dies when it is done.
