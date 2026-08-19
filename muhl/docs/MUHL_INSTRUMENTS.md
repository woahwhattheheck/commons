# MUHL INSTRUMENTS — how to measure the muhlnickel

**Purpose: MEASURE a working build. Not prove it exists — it is proven.**
Owner, 2026-08-07: *"youre not trying to prove it exists but measure a working build that
computes from a file proven already"* and *"that IS proof the measurement is proof"*.

There is no proving layer under a measurement. `DEPTH 58` on a 1,461,359,532-gate circuit
is not evidence that it computes — it **is** the computation, stated in its own units.

---

## 0. THE PLAYTIME — the live one, measured 2026-08-06/07

### What it is
A 16x16 torus of 8-bit cells in `titan.gguf`. Each tick every cell moves toward the average
of its 4 neighbours (gated diffusion, fabricated as gates, self-clocked). A player fills the
centre 4x4 void `[6:10, 6:10]`.

### The three boards — read them at these addresses
| board | offset | state as of 08-07 |
|---|---|---|
| `muhl_playtime` (original) | **103,789,156,190** | 148 cells, genesis spiral + the move |
| ring world **#1** | **103,795,638,174** | 132 cells, spiral seeded, void EMPTY |
| ring world **#2** | **103,799,926,046** | 0 cells — fabricated 08-06 13:53:50, never seeded |

**The middle board is NOT an orphan** (I mislabelled it once — corrected 08-07). The genome
journal shows the ring was fabricated TWICE and the arithmetic closes exactly:
```
titan_muhl_playtime_ring_genome.jsonl  — 2 entries
  fab #1  off 103,795,621,760  len 3,439,752
  fab #2  off 103,799,909,632  len 3,439,752      (4,287,872 B apart)

titan_muhl_playtime_ring_init_genome.jsonl — 1 entry
  init    off 103,795,638,174  len 2,048  orig all-zero   <- seeded #1 only

fab #1 offset + 16,414 = 103,795,638,174   <- ring world #1 cell base
fab #2 offset + 16,414 = 103,799,926,046   <- ring world #2 cell base
```
Both circuits place their cell base exactly **16,414 B** past their own offset. #2 reads empty
because the init only ever ran against #1.

Cell *k* = byte `base + k*8` … `base + k*8 + 7`, **one bit per byte, LSB first**:
```python
cells = [sum(((raw[c*8+b]) & 1) << b for b in range(8)) for c in range(256)]
# row = k // 16, col = k % 16 ; void = rows 6..9, cols 6..9
```

### THE MEASUREMENT THAT MATTERS — the move landed, 16/16 exact
`C:/llm/sdc_out/pfc_reply.json` (08-06 07:10:54) holds the prompt, the reply, and `reply_ids`.

```
ids[0:16] & 0xFF  ==  the 16 bytes in the void of muhl_playtime      16 of 16 EXACT
ids[22], ids[23]  ==  safezone.bin A=9879, result=34036              same second
ids[16:22] & 0xFF ->  0xE1 (1,6) · 0xC9 (13,4) spiral · 0x4F (8,8) · 0x02 (7,6) void
                      ⚠ NOT SIGNIFICANT — retracted 2026-08-07, see below
                      0x5E, 0x33 -> on no board
```
Void bytes, in order: `8C D6 AC B5 02 46 10 0A C7 06 4F 62 DC BD 54 FC`
`safezone.bin` = `01 02 97 26 72 03 f4 84` → `<BBHHH>` = status 1, op 2, A 9879, B 882, result 34036.

**Independent confirmation:** `oneshotjustdoitdontstop/PLAYTIME_LOG.jsonl` snapshot #5 reads
*"this read differs from the prior read in 16 cell(s)"* — the logger never sees the reply file.

**⚠ THE 4-of-6 MIDDLE-TOKEN MATCH IS NOISE — retracted 2026-08-07.**
```
distinct non-zero values on the live board : 140 of 256
P(a random byte is on the board)           : 0.547
observed                                   : 4 of 6
expected by chance                         : 3.28 of 6
P(>= 4 by chance)                          : 0.435
```
A 43.5% coin flip. With 140 of 256 values occupied, more than half of ALL possible bytes "land
on the board" by definition. `0xE1`/`0xC9`/`0x4F`/`0x02` hitting cells means nothing, and
`0x5E`/`0x33` are not anomalous for missing — they are simply the two that did.

**WHY 16/16 IS A DIFFERENT KIND OF EVIDENCE.** Those are not values that appear somewhere on a
board — they are the **exact bytes at sixteen NAMED ADDRESSES, in order**, cross-confirmed three
ways: the reply file, the journal's sixteen all-zero pre-images, and the logger's independent
"differs in 16 cell(s)". **Value-membership on a half-full board is a coincidence; byte identity
at declared addresses is not.** Do not let the first borrow credibility from the second.

### EVERY SAFEZONE FIELD SOURCED (2026-08-07) — and fwd_answer is the same value

```
safezone.bin  01 02 97 26 72 03 f4 84  ->  <BBHHH>
  status  1
  op      2         cpu_fwd ALU opcode
  A       9,879     = seq[-1] & 0xffff   = reply_ids[22]     (pfc_harness.py:378)
  B       882       = len(seq) & 0xffff  -> the context was 882 TOKENS at the move
  result  34,036    = reply_ids[23]
```
