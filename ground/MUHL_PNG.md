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
