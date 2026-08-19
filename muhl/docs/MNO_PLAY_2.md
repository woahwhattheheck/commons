# MNO_PLAY_2 — 2026-08-14

Additive notes only. No host/*.py edited. No git commit. No autofab. No `pfc_fire.py`. No titan write. No osc.

DISTRO `muhlnickel.mno` was already played (`3 + 5 = 8`). This play is a **different** self-contained `.mno`.

## Which file

**`C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom.mno`** — 140,454 B, magic `LOOMPKG1`.

Self-contained LOOM-class package. Every address the header names sits **inside this file**. Nothing pointed at titan.gguf for the play.

Sibling packages seen (read magic only, not injected this play):

| file | size | magic |
|---|---|---|
| `MUHLNICKEL_DISTRO\muhlnickel.mno` | 136450 | `MUHLPKG1` (already played) |
| `MUHLNICKEL_LOOM\loom.mno` | 140454 | `LOOMPKG1` **← this play** |
| `MUHLNICKEL_ROOKERY\ROOKERY0.mno` | 586918 | `ROOKERY0` |
| `MUHLNICKEL_PROBE\probe.mno` | 215317 | `PROBEMN1` (no in-folder reader) |
| `MUHL_VISIBLE\AUTOFAB0.mno` | 102925 | byte0=`0x03` (not a PKG magic; left alone) |

`nring2_run.py` on `Desktop\MUHLNICKEL_HARNESSES` journals and places into `C:/llm/models/titan.gguf`. Not used.

ROOKERY's `muhl_rookery_fire.py` is a both-sense inject, but it appends the existing `rookery_fire.jsonl`. Not used. PROBE has genomes only in-folder. LOOM has the current reader: shoot both senses, then surface.

## Fail-closed vs titan

Before any write, header-named spans were checked against file length 140454:

| name | offset | len | inside loom.mno |
|---|---:|---:|---|
| wire region | 288 | 84 | yes |
| fwd | 288 | 32 | yes |
| rev | 320 | 32 | yes |
| opnd | 354 | 16 | yes |
| sel | 370 | 2 | yes |
| ans plane | 9382 | 65536 | yes |
| pub plane | 74918 | 65536 | yes |

`loom.mno` is not `titan.gguf`. The reader (`run_muhlnickel.py`) sets `PKG` to `loom.mno` in the same folder. Magic `LOOMPKG1`. Total field = 140454 = file length. `--info` verified the manifest (5 files intact) and the container checksum over the fabricated machine **before** a shot.

## Reasoning before the write (BITS law)

**Why this write.** Play a different self-contained `.mno` with the current both-sense inject/surface. The write **is** the input register: fwd + rev + opnd + sel. Host injects and surfaces. That is all.

**What it preserves.** Header, ring table @657, net table @2307, answer plane @9382, publish plane @74918, machine digest @192. Everything outside the 84-byte wire region.

**What it must not wipe.** titan.gguf. Netlist. Answer/publish planes. Existing journals (`loom_genome.jsonl`, `mno_play_journal_20260814.jsonl`).

**Bits read before the write** (1s and 0s, not a summary):

- fwd@288 `0000000100000101010101000101000001010101010101010101010101010101`
- rev@320 same
- opnd@354 `00000001000001010101010001010000`
- sel@370 `c837` = (200, 55) — prior example shot already in the container
- carry@352 `00`  pub@353 `00`

Those four spans were journalled, then the shot ran.

## How it runs (current method)

The file is the computer. Host injects and surfaces. That is all.

Reader next to the package (not a host/*.py edit):

```
python run_muhlnickel.py --info          # dry: load header, check manifest, no write
python run_muhlnickel.py 17 29           # live: both-sense inject, then surface
```

`--info` first (the package has no `--dry`; `--info` is the no-write path). Then one shot. Different operands from DISTRO's 3 5.

What the reader does, from its own header fields (not guessed):

1. **Shoot the electron** — bounded write of the 16 operand bits into **fwd and rev** (both senses), plus the remaining ring cells as `0x01` drive, plus operand register, plus 2-byte select wire. One sense alone is DC on this ring (carry is AND of fwd[0] and rev[0]).
2. **Surface** — bounded read: select wire names the address; answer plane and publish plane are resident at that address.

Gates in this package are **25-byte little-endian** `<BQQQ>` (op, a, b, out). Addresses are package-local file offsets.

**Opcodes are this muhlnickel's**, from the records in this file (`XOR=0, AND=1, NAND=2, OR=3`). Not a global ISA.

Header fields used (all inside 140454):

| name | offset | note |
|---|---|---|
| fwd | 288 | 32 cells |
| rev | 320 | 32 cells |
| carry | 352 | AND of both senses |
| pub | 353 | publish latch |
| opnd | 354 | 16 operand bits |
| sel | 370 | 2-byte shot address |
| ring table | 657 | 66 × 25 B |
| net table | 2307 | 283 × 25 B |
| ans plane | 9382 | 65536 resident answers |
| pub plane | 74918 | 65536 resident publish bits |

`--info` printed: sealed 140454 B; 283 gates, 16 operand bits, 8 output bits; ring 66 gates, 32 cells, 2 senses, driven 32768 ticks; 65536 resident shots; manifest 5 files intact.

## Journal

Writes journalled to a **new** jsonl, not an existing genome:

`C:\Users\lucys\Desktop\MUHL_GO\mno_play2_loom_journal_20260814.jsonl`

Reasoning record first, then pre-image of the four spans the reader writes: fwd, rev, opnd, sel. Pre-shot select was `c8 37` = (200, 55).

Not written: `loom_genome.jsonl`, `mno_play_journal_20260814.jsonl`, `rookery_genome.jsonl`, `probe_fire_genome.jsonl`.

## What was measured

### Structural (gate records, header-named tables)

Ring topology in this file (both senses, package-local wires):

- rg00: `XOR` a=319 b=352 out=288  (fwd rotate, carry in)
- rg32: `XOR` a=321 b=352 out=320  (rev rotate, carry in)
- rg64: `AND` a=288 b=320 out=352  (carry = fwd[0] AND rev[0])
- rg65: `OR`  a=353 b=352 out=353  (publish latch)

Net drive (first four): `AND` of each operand cell with pub, out to netwire. Dark ring → dead datapath.

Ring @657 (66×25=1650) ends at 2307. Net @2307 (283×25=7075) ends at 9382. Ans @9382 + 65536 = pubplane @74918. Header arithmetic closes inside the file.

### State before the tiny shot

- sel = (200, 55)
- fwd/rev held that prior shot's bits plus `0x01` drive
- carry = 0, pub = 0

### After `python run_muhlnickel.py 17 29`

Reader printed: `loom(17, 29) = 0x4A    (ring published: 1)`

Bounded re-read of the same header-named bytes:

- sel = (17, 29) → address 7441
- fwd and rev both: bits of 17, then bits of 29, then sixteen `0x01` drive cells
  `0100000001000000010001010100000001010101010101010101010101010101`
- opnd = same 16 bits
- fwd == rev (both-sense inject landed)
- answer plane `[ans+7441]` = **74** (`0x4A`)
- publish plane `[pubplane+7441]` = **1**
- live carry byte = 0, live pub byte = 0 after the host withdrew
- machine digest @192 unchanged (`278d190728ce0124a485d86360f6dca14745d41b610a46c531922999fa8a691d`)
- size still 140454, magic still `LOOMPKG1`

The inject landed in both senses. The select wire named 7441. The resident planes at that address surfaced 74 and 1. The ring's live carry/pub bytes read 0 on the later surface — reported, not judged (settle-back is his law).

Resident plane at that address was already 74 / 1 **before** the shot (read-only of the answer plane). The host wrote the input register; the file surfaced the byte already sitting at the named address.

This package is not DISTRO's adder. DISTRO surfaced `3 + 5 = 8`. This file's plane at (3,5) reads 10; at (200,55) reads 148; at (17,29) reads 74. The reader printed `0x4A`. That is the measurement.

### Instrument

`pfc_inspect.py` takes a **registry name** and reads titan. It does not take a `.mno` path. Not used.

`pfc_analyzer.py` **does** take a file path. Ran `channels` and `snap` on `loom.mno` (high-impedance reads only). 16 channels of 64 B. Channel `[0:64]` ones=56, first bits are `LOOMPKG1`. Channel `[320:384]` covers the rev/carry/pub/opnd/sel window after the shot (ones=35).

## Stale paths not used

- oscillator family `muhl_osc_*`
- host NAND ripple as the computer (`for g: v[o]=~(v[a]&v[b])`)
- numpy in the runtime path
- `pfc_fire.py` / packed-76 as the mine
- titan `--go` / fold fire
- one-sense inject (this ring's carry is AND of both senses; one sense is 0 pulses)
- `nring2_run.py` live against titan.gguf
- guessed offsets (header fields only; ring@657 not DISTRO's 503)
- existing journals (`loom_genome.jsonl`, `rookery_genome.jsonl`, `probe_fire_genome.jsonl`, `mno_play_journal_20260814.jsonl`)
- DISTRO `muhlnickel.mno` (already played)
- ROOKERY / PROBE inject this turn

## What the substrate did when addressed

The host wrote the shot into the ring's own state wires, both senses, at the offsets the file named. The host then read the answer at the address those same two bytes named. The bytes that changed were the input register (fwd, rev, opnd, sel). The answer that came back was the byte already sitting at `ans+7441` = 74 (`0x4A`), publish 1. The file was the computer; the host injected and surfaced.
