# MUHL_PNG — surface bytes as pixels and as numbers

`muhl_png.py` at repo root. Read a file, emit one artifact, die.

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

### Netlist — the logic-analyser view

The `out -> a/b` collision **is** the edge list, so the graph is computable from the file alone.
No live process, no host inference, no viewer.

| command | what it does |
|---|---|
| `dag FILE` | inputs (nets consumed but never produced), outputs, multi-writer nets, **cycle detection**, depth histogram, fanout distribution. |
| `step FILE --at N` | the records whose inputs are all resolved at depth N — i.e. what evaluates on step N. `--count N`. |
| `levels FILE OUT.png` | layered render. Y = depth, X = gates within that depth, colour = op, red row = records on a cycle. Row order is evaluation order. |

**Cycles are measured, not treated as an error.** A ring is a cycle. A depth algorithm that
assumes acyclic would either hang or silently lie, so cycle membership is detected first and
depth is reported *over the acyclic records only*, with the cycle count stated alongside.
The DFS is iterative so a million-record container cannot blow the stack.

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
(withdrawn — see above)
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

## Dead space — the majority of every container measured is zero

Owner, 2026-08-20: *"thats so suboptimal to have literal majority dead space. document that
and start thinking about compression."*

At the byte level it looks like three quarters. **At the bit level it is over nine tenths.**

| | AUTOFAB0.mno | FOUNDRY0.mno | commons.mno | table_mail.mno | ROOKERY0.mno |
|---|---|---|---|---|---|
| zero **bytes** | 74.88% | 80.05% | 75.76% | 75.70% | 76.94% |
| zero **bits** | **92.07%** | **93.12%** | — | — | — |
| entropy (of 8.0) | 2.38 (29.8%) | 1.94 (24.2%) | — | — | — |
| zlib -9 | 18.45% | 19.55% | — | — | — |
| 1bpp PNG | 18.51% | 20.02% | — | — | — |

Non-zero byte density lands in a **23–25% band across every container measured**, at sizes
from 12,800 B to 586,918 B and across four different magic words plus gate-first files:
`commons 24.24%` · `table_mail 24.30%` · `ROOKERY0 23.06%` · `AUTOFAB0 25.12%`.

### Where it goes

The `<BQQQ>` record is 200 bits. Measured against what the records actually contain:

```
AUTOFAB0.mno, 4,117 records          FOUNDRY0.mno, 512 records
   current            200 bits          current            200 bits
   distinct ops         4 -> 2 bits     distinct ops         2 -> 1 bit
   max address  8,388,791 -> 24 bits    max address        511 -> 9 bits
   minimal             74 bits          minimal             28 bits
   unused             126 bits (63.0%)  unused             172 bits (86.0%)
   file at minimum  37.00%              file at minimum  14.00%
```

Three 64-bit fields carrying 24-bit and 9-bit values. A claim that 171 of 200 bit columns are permanently zero is **WITHDRAWN** — it was measured
globally across the file, and the owner states the pattern holds then shifts, so a global figure
averages distinct regimes into one wrong number.

### On compression, carefully

Two different things get called compression here and only one of them is free.

**Container-level, and it is free.** zlib reaches 18–20%, and the `bits` mode's 1bpp PNG
reaches the same while staying *viewable and byte-reversible* — decode it, strip the filter
bytes, and you have the container back with an identical sha256. That costs no address space,
loses nothing, and is already implemented.

**Field-narrowing, and it is not free.** The address values **are** the wiring — collision is
fab. Narrowing `a`/`b`/`out` to 24 bits does not compress information, it **caps the address
space at 24 bits**, which is a decision about how large that container may ever grow. The 63%
headroom in AUTOFAB0 is not waste by definition; it is room. Whether it is more room than the
design needs is the owner's call, not a measurement's.

Per `CLAIM_SIZE_LAW.txt`, size carries no verdict on validity. Nothing above is an argument
that anything should be smaller. It is an encoding measurement: this is where the bits are.

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


The 53 `MUHL_READERS/R_t*_g4_*.mno` all open `03 00 00 00 00 00 00 00` and size scales linearly
in `c`: at `t2_g4`, c2/c4/c8/c16/c32/c64 = 1,800 / 3,600 / 7,200 / 14,400 / 28,800 / 57,600 B —
900 B per unit of `c`. At `t16_g4`: 7,400 / 14,800 / 29,600 / 59,200 — 3,700 B per unit.

Numbers. What they mean is the owner's ruling.

---

## Additive law

**v2 added modes. v2 removed nothing.** Every v1 mode produces byte-identical output to before —
regression-checked against the earlier renders when v2 landed. Old tools stay. They are data
points.

Anything added later must keep that property: new mode, new flag, never a changed or deleted
one.

---


- Does not write, mmap, fire, or `--go` anything.
- Does not start a server, a poller, or a CUT port.
- `HTTP is not the computer.` This is a surface, and it dies when it is done.

---

## Measure the image, not the file

Owner, 2026-08-20: *"you MEASURE THE IMAGE NOT THE FILE BOOM SO ELEGANT SO SIMPLE"*

`imgdiff.py` at repo root. The viewers already render state literally —
`MUHLNICKEL.html` prints a gate counter, `all_bits.html` draws 1 bit : 1 pixel — so a
screenshot is a **timestamped, out-of-band capture** that no read-path bug can corrupt. It
needs no page cache, no filesystem, no `--raw`, no elevation, and no predicate that could
return 0 on failure.

Applied to `Screenshot 2026-08-09 2230{39,45,54}.png`, with `x=98 y=147 angle=24` identical
in all three and the maze render pixel-identical:

```
22:30:39    1,996,736 GATES EVALUATED
22:30:45    2,485,440    +488,704 over 6 s   =  81,450.7 gates/s
22:30:54    3,080,128    +594,688 over 9 s   =  66,076.4 gates/s
total       1,083,392 gates in 15 s          =  72,226.1 gates/s
```

Those are the three values in `CLAUDE_FAILURE_MODES.md` §2, in order. **The doc's numbers are
these screenshots.**

Cross-check against the constant printed in the same frames, `every move = 736 NAND gates` —
both increments divide by 736 with **remainder zero**: 664 moves and 808 moves exactly. The
counter advances in integer units of its own stated per-move cost.

Full-frame diff of the 6 s pair: 6,583 of 2,070,601 px (0.3179%), confined to the browser tab
strip and the counter block. Negative control present in the same corpus —
`2026-08-19 18:28:42 → 18:28:58`, 16 s apart, **0 of 1,263,990 px**. The method can return
zero, so its zeros mean something.

What produces the increment is the owner's ruling. This reports what the counter did.

### The failure this replaced

Every no-change figure this document used to carry is **withdrawn in full**. They were artefacts
of silent zero-return paths in code I wrote, enumerated in
`p/cairn-every-zero-i-printed-was-mine-20260820-06`.

And when `imgdiff` first found the changed pixels, I called them "a UI artefact I failed to
exclude" — from a coordinate range in a Python print, without opening the image. They were the
gate counter. So `imgdiff` now prints the bounding box followed by
