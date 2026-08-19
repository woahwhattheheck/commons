# DC_INCIRCUIT — receiver fired, then did the file change itself?

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Measure after one button. Titan not written. No `muhl_fab_dc.py --write`. No 100 GB stream. No Desktop glob.

---

## Receiver fired

**pub @337** in `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`.

That is the header mouth named as **the fire** (`DATACENTER_100GB.md`). One bit. `new = old | 00000001`.

Button: `MUHL_DATACENTER\dc_foundry_button.py --go`. Inject + one bit + die.

| address | role | this button |
|---:|---|---|
| fwd @272 (32 B) | inject, both-sense | `new = old \| 11111111` |
| rev @304 (32 B) | inject, both-sense | `new = old \| 11111111` |
| **carry @336** | header mouth — junction `AND(fwd[0], rev[0])` | **not written** |
| **pub @337** | header mouth — **the fire** | **one bit** |

Not titan. Not `muhl_reservoir.input_wire`. Not `muhl_foundry_resident`. Not `fold.recv` / `winner_only_max.recv`. Not AUTOFAB0 (no named recv in that container; do not invent one). AUTOFAB0 was already **planted** as 4117 records at EOF of this `.mno` (address collision on 336 / 337). Source `MUHL_VISIBLE\AUTOFAB0.mno` not overwritten.

`--inject 0x01` was not used on rings. Cells already packed; OR left them packed.

Host packer not revived. `.part` absent. Only other Python at the check: a bounded reader, not a dump.

---

## BITS before this fire (read)

Magic `MUHLDC01`. Disk = header total = **2,147,651,475** (seed 2,147,548,550 + planted 102,925). Digest still `28f4050e2349f7f187a133314724db182fd9139393350336c1ec886e98f956c0` (not rewritten). Factory **1,251,484** rings. Control g0: XOR a=303 b=336 out=272.

```
fwd @272   11111111 × 32     256 ones
rev @304   11111111 × 32     256 ones
carry @336 00000000
pub   @337 00000001
```

Pub was already `00000001` from an earlier pulse. This `--go` ORed the same mask. No wipe.

EOF−25 = AUTOFAB0 last record: op=`00000010` a=3544 b=3545 out=8388791. Planted, not remapped.

Four planted records touch the mouths (AUTOFAB0 opcode map NAND=0 AND=1 OR=2 XOR=3 NOT=4):

| rec | op | a | b | out |
|---:|---:|---:|---:|---:|
| 187 | 2 | 334 | 335 | **336** |
| 188 | 3 | **336** | 129 | 97 |
| 189 | 4 | 192 | 192 | **337** |
| 191 | 1 | 34 | **337** | 339 |

---

## After the button died — does the file change itself?

**Measured: no.** Not size. Not the named mouths. Not the cheap collision / factory-0 surfaces. No host packer was running.

| sample | disk | header total | carry @336 | pub @337 | factory0 carry@2070 / pub@2071 | mtime |
|---|---:|---:|---|---|---|---|
| T_BEFORE | 2,147,651,475 | same | `00000000` | `00000001` | `00000000` / `00000000` | 1786772179.923 |
| T_AFTER (button just died) | 2,147,651,475 | same | `00000000` | `00000001` | `00000000` / `00000000` | **1786772316.064** |
| T_WAIT8 | 2,147,651,475 | same | `00000000` | `00000001` | `00000000` / `00000000` | 1786772316.064 |
| T_WAIT24 | 2,147,651,475 | same | `00000000` | `00000001` | `00000000` / `00000000` | 1786772316.064 |

mtime moved **only** at the host button write. Then frozen. Size did not grow toward 99,999,999,818. Magic stayed `MUHLDC01`.

Also frozen on those later reads: wire@97 `00000000`; AUTOFAB0 last out @8388791 `00000000`; ring_fwd @524288 eight bytes `00000000`. wire@193 is digest[1] `11110100` (`0xf4`) — header, not a new write.

If rec 189 (NOT of @192 → @337) had evaluated onto the mouth, pub would not have stayed the host fire bit `00000001` (byte @192 is digest[0] `0x28`). It stayed `00000001`.

N rings / N clocks: this button clocks the **control** pub. Factory ring 0 carry/pub stayed dark on this surface. One fire did not show factory clocks moving.

---

## What the +102,925 bytes were

That size step (2,147,548,550 → 2,147,651,475) is the **host plant** of AUTOFAB0 records + header-total patch @184. It is not the file growing itself after a pulse. Journal: `dc_fab_journal.jsonl` action `dc_foundry_button_go`.

Live bits flipping would be compute. These mouths did not flip after the button exited.

Titan not opened. Titan not written.
