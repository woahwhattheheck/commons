# MNO_PLAY — 2026-08-14

Additive notes only. No host/*.py edited. No git commit. No autofab. No `pfc_fire.py`. No titan write.

## Which file

**`C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno`** — 136,450 B, magic `MUHLPKG1`.

Self-contained DISTRO-class package. Every address the header names sits **inside this file**. Nothing pointed at titan.gguf for the play.

Sibling packages seen (read magic only, not injected):

| file | size | magic |
|---|---|---|
| `MUHLNICKEL_DISTRO\muhlnickel.mno` | 136450 | `MUHLPKG1` |
| `MUHLNICKEL_LOOM\loom.mno` | 140454 | `LOOMPKG1` |
| `MUHLNICKEL_ROOKERY\ROOKERY0.mno` | 586918 | `ROOKERY0` |
| `MUHL_VISIBLE\AUTOFAB0.mno` | 102925 | byte0=`0x03` (not a PKG magic; left alone) |

`nring2_run.py` on `Desktop\MUHLNICKEL_HARNESSES` was **read, not run**. It journals and places into `C:/llm/models/titan.gguf`. That is the titan-addressing harness. Not used.

## How it runs (current method)

The file is the computer. Host injects and surfaces. That is all.

Reader next to the package (not a host/*.py edit):

```
python run_muhlnickel.py --info          # dry: load header, check manifest, no write
python run_muhlnickel.py 3 5             # tiny live: both-sense inject, then surface
```

`--info` first (the package has no `--dry`; `--info` is the no-write path). Then one shot.

What the reader does, from its own header fields (not guessed):

1. **Shoot the electron** — bounded write of the 16 operand bits into **fwd and rev** (both senses), plus the remaining ring cells as `0x01` drive, plus operand register, plus 2-byte select wire. One sense alone is DC on this ring (carry is AND of fwd[0] and rev[0]).
2. **Surface** — bounded read: select wire names the address; answer plane and publish plane are resident at that address.

Gates in this package are **25-byte little-endian** `<BQQQ>` (op, a, b, out). Addresses are package-local file offsets.

**Opcodes are this muhlnickel's**, from its fabricator (`XOR=0, AND=1, NAND=2, OR=3`). Not a global ISA. A different `.mno` can number them differently.

Header fields used (all inside 136450):

| name | offset | note |
|---|---|---|
| fwd | 288 | 32 cells |
| rev | 320 | 32 cells |
| carry | 352 | AND of both senses |
| pub | 353 | publish latch |
| opnd | 354 | 16 operand bits |
| sel | 370 | 2-byte shot address |
| ring table | 503 | 66 × 25 B |
| net table | 2153 | 129 × 25 B |
| ans plane | 5378 | 65536 resident answers |
| pub plane | 70914 | 65536 resident publish bits |

`--info` printed: sealed 136450 B; 129 gates, 16 operand bits, 8 output bits; ring 66 gates, 32 cells, 2 senses, driven 32 ticks; 65536 resident shots; manifest 5 files intact.

## Journal

Writes journalled to a **new** jsonl, not an existing genome:

`C:\Users\lucys\Desktop\MUHL_GO\mno_play_journal_20260814.jsonl`

Pre-image of the four spans the reader writes: fwd, rev, opnd, sel. Pre-shot select was `c8 37` = (200, 55) — a prior example shot already in the container.

## What was measured

### Structural (gate records, header-named tables)

Ring topology in this file (both senses, package-local wires):

- rg00: `XOR` a=319 b=352 out=288  (fwd rotate, carry in)
- rg32: `XOR` a=321 b=352 out=320  (rev rotate, carry in)
- rg64: `AND` a=288 b=320 out=352  (carry = fwd[0] AND rev[0])
- rg65: `OR`  a=353 b=352 out=353  (publish latch)

Net drive (first four): `AND` of each operand cell with pub, out to netwire. Dark ring → dead datapath.

Guessing "gates start at byte 224" was closed. Byte 224 is `outs_off` (8 output addresses). The header names the tables: ring@503, net@2153.

### State before the tiny shot

- sel = (200, 55)
- fwd/rev held that prior shot's bits plus `0x01` drive
- carry = 0, pub = 0

### After `python run_muhlnickel.py 3 5`

Reader printed: `3 + 5 = 8    (ring published: 1)`

Bounded re-read of the same header-named bytes:

- sel = (3, 5) → address 1283
- fwd and rev both: bits of 3, then bits of 5, then sixteen `0x01` drive cells
- opnd = same 16 bits
- answer plane `[ans+1283]` = **8**
- publish plane `[pubplane+1283]` = **1**
- live carry byte = 0, live pub byte = 0 after the host withdrew

The inject landed in both senses. The select wire named 1283. The resident planes at that address surfaced 8 and 1. The ring's live carry/pub bytes read 0 on the later surface — reported, not judged (settle-back is his law).

### Instrument

`pfc_inspect.py` takes a **registry name** and reads titan. It does not take a `.mno` path. Not used for this play.

`pfc_analyzer.py` **does** take a file path. Ran `channels` and `snap` on `muhlnickel.mno` (high-impedance reads only). 16 channels of 64 B. Channel `[0:64]` ones=54, first bits are `MUHLPKG1`. Channel `[320:384]` covers the rev/carry/pub/opnd/sel window after the shot.

## Stale paths not used

- oscillator family `muhl_osc_*`
- host NAND ripple as the computer (`for g: v[o]=~(v[a]&v[b])`)
- numpy in the runtime path
- `pfc_fire.py` / packed-76 as the mine
- one-sense inject (this ring's carry is AND of both senses; one sense is 0 pulses)
- `nring2_run.py` live against titan.gguf
- guessed offsets (224-as-gate-table was wrong; failed closed and used header fields)
- existing journals (`titan_nring2_run_genome.jsonl`, `loom_genome.jsonl`, `rookery_genome.jsonl`, `foundry_live_genome.jsonl`)

## What the substrate did when addressed

The host wrote the shot into the ring's own state wires, both senses, at the offsets the file named. The host then read the answer at the address those same two bytes named. The bytes that changed were the input register (fwd, rev, opnd, sel). The answer that came back was the byte already sitting at `ans+1283`. The file was the computer; the host injected and surfaced.
