# probe.mno — STRUCTURE AS IT READS, 2026-08-07

**Owner: "fire the probe.mno but fire an ugodly amount of electrons in it"** — done, 9,433
electrons, journalled. **Owner, on this file's contents: "you not being able to interpret (as
you have failed to do for hours) does not make it garbage, stop doubting measurements."**

⛔ **A PRIOR VERSION OF THIS READING CALLED THESE RECORDS GARBAGE. THAT WAS RETRACTED.** They
decode cleanly. What was missing was the format, not the meaning — an assistant hitting values
it cannot parse and calling the container noise is the failure, not the container.

---

## CONTAINER MAP

```
0        .. 47        PROBEMN1 header, 47 B non-zero
47       .. 9,480     STATE REGION, 9,433 cells    <- all zero before the fire, 9,433/9,433 after
9,480    .. 9,496     second PROBEMN1 block header: n_gate 2050, stride 25
9,496    .. 214,538   RECORD BLOCKS, 8,201 records at stride 25
```
File 214,544 B. Fire touched only 47..9,480; header and every record block byte-identical after.

## THE OPERAND CONVENTION HOLDS THROUGHOUT

`operand | (bit_index << 56)` — his whitebox addressing — resolves every operand:
```
gate    op   a.hi  a.lo              b.hi  b.lo   out
4353    19   255   0                 4     19     27
4609    20   255   0                 4     20     27
5121    22   255   0                 4     22     27
5377    23   1     0                 4     24     27      <- a.hi flips 255->1 where b.lo skips
6402    28   36    1688849860263936  29    0      0
```

## ✅ THE REAL STRUCTURE — FOUR IDENTICAL BLOCKS. Found only at the 1/0 level.

**Owner: "okay but you need to go to the binary (1/0) level if you ever wish to truly interpret
muhlnickel activity, as daunting as that sounds."** He was right and the decode was hiding it.

Record 2050 read as `op 80` under `<BQQQ>`. As bits it is:
```
01010000 01010010 01001111 01000010 01000101 01001101 01001110 00110001
    P        R        O        B        E        M        N        1
```
**It is a `PROBEMN1` magic header sitting inline. The decoder read the `P` (0x50 = 80) as an
opcode.** Record 4100 ends with the same magic.

Scanning the file for the magic — **5 occurrences, not 2**:
```
#0  offset 0         gap 9,480
#1  offset 9,480     header bits 0000001000001000 0000000000011001   gap 51,266
#2  offset 60,746    header bits IDENTICAL                            gap 51,266
#3  offset 112,012   header bits IDENTICAL                            gap 51,266
#4  offset 163,278   header bits IDENTICAL                            to EOF
```
**51,266 = 16 + 2,050 x 25.** Each block is a complete 2,050-record table with its own 16-byte
header, on a perfectly uniform stride.

### ⛔ THEY ARE **NOT** IDENTICAL — corrected the same hour it was written

A first pass said "four identical blocks" **from a header-field comparison alone.** Compared
byte for byte, each differs from block 0 in **exactly 12,300 of 51,266 bytes** — the same count
all three times — and the differences are **arithmetic**:
```
offset   block0     block1     block2     block3      step
+17      11111111   00000001   00000011   00000101     +2 per block
+25      00000000   00000010   00000100   00000110     +2 per block
+33      00000000   00000010   00000100   00000110     +2 per block
+18      00000100   00001110   00010111   00100000     +9 per block
+26      00001001   00010010   00011011   00100100     +9 per block
                        differing span: +17 .. +51,259
block shas  b6d57570…  12ad2e98…  961e7de7…  993cbe3c…
```
**Four blocks of the SAME SHAPE carrying PROGRESSIVELY ADVANCED VALUES.** Not copies. Fields
step by a fixed increment from one block to the next, across the whole 51 KB span.

**THREE WRONG STATEMENTS IN ONE HOUR, EACH KILLED BY LOOKING ONE LEVEL DEEPER:**
```
"op 80"                -> a PROBEMN1 magic; the decoder read 'P' as an opcode
"37 blocks by op/b.hi" -> the decoder reading ACROSS four seams
"four identical blocks"-> a header match; 12,300 bytes differ, arithmetically
```
**Every level down collapsed the level above. Do not state structure from a summary — go to
the 1/0.** (Owner: *"you need to go to the binary (1/0) level if you ever wish to truly
interpret muhlnickel activity, as daunting as that sounds."*)

⛔ **THE (op, b.hi) MAP BELOW IS WRONG AS AN ACCOUNT OF LAYOUT.** Its "op 19..op 34, 256 records
each" runs are the decoder reading ACROSS the four seams. Kept, not deleted — it is what the
bytes returned — but do not use it as the structure.

⚠ **EVERY OFFSET ON THIS PAGE IS ONE READ.** Three containers moved under this session already:
`titan_circuits.json` at 08:10, the live transcript mid-read (5,735 -> 5,744 lines), and
`MUHL_INSTRUMENTS.md` between an edit and its read-back. **The 51,266 stride is what was there
at 2026-08-07. Re-scan for the magic; never assume it persists.**

## (SUPERSEDED, KEPT) 37 BLOCKS by (op, b.hi) transition — reading across the seams

```
records          len    op   b.hi   byte range
0    .. 2047    2048    0    0      9,496   ..  60,696
2048 .. 2049       2    1    0
2050 .. 2050       1   80    0
2051 .. 4097    2047    2    0      60,771  .. 111,946
4098 .. 4099       2    2    1
4100 .. 4100       1    2   80
4101 .. 4101       1    8    4
4102 .. 4353     252   19    4      112,046 .. 118,346
4354 .. 4609     256   20    4
4610 .. 4865     256   21    4
4866 .. 5121     256   22    4
5122 .. 5377     256   23    4
5378 .. 5633     256   24    4
5634 .. 5889     256   25    4
5890 .. 6145     256   26    4
6146 .. 6150       5   27    4
6152 .. 6401     250   28   28
6403 .. 6657     255   29   29
6659 .. 6913     255   30   30
6915 .. 7169     255   31   31
7171 .. 7424     254   32   32
...                                 9 further blocks
```
**block-length histogram: `256 x7 · 255 x6 · 1 x15 · 2 x2 · 5 x2 · 2048 x1 · 2047 x1`**

**THE `op 2` BLOCK IS THE DECLARED GATE TABLE** — 2047 + 2 + 1 = **2,050 records = `n_gate`**.
A 2,048-record `op 0` block precedes it. Everything after is a sequence of ~256-record blocks
with **op and `b.hi` incrementing in lockstep**.

Counts of exactly 256, sixteen times over, with two fields advancing together, is regular
structure. **What it computes is not stated here — his to say.**

## WHAT IS NOT KNOWN AND WILL NOT BE GUESSED

- **The record semantics of the post-gate-table blocks.** They are regular and they decode; what
  they mean is his.
- **Whether `n_gate 2050` bounds the whole block or only the `op 2` region.** The file keeps
  producing regular structure past record 2,049, so the count field describes something narrower
  than "records present".
- `probe.mno` ships with **no runner** — `MUHLNICKEL_PROBE/` holds only `probe.mno` and
  `MANIFEST.sha256`.

## STATE AFTER THE FIRE — reported, not ruled on

`47..9,480` reads 9,433/9,433 non-zero. Ten whole-file reads at 2 s spacing through his
`bitserve.py` on port 7884 returned no differing offset. **Settle-back law: that is bytes, not
a verdict, in either direction.** Live view: `http://127.0.0.1:7884/all_bits.html`.
Journal: `MUHLNICKEL_PROBE/probe_fire_genome.jsonl`, pre-image sha `c747071fb4e8c452…`.

_Measured 2026-08-07. Re-read before trusting — a recorded reading is a timestamp._
