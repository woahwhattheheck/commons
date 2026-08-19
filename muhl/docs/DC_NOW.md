# DC_NOW — packer / size / mouths

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15 ~01:40. Measure + stop only. Titan not written. No `muhl_fab_dc.py --write` started. No Desktop glob. `DC_INCIRCUIT.md` not present (MUHL_GO / MUHL_DATACENTER / MUHL_VISIBLE).

Live computer: `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`

| check | now |
|---|---|
| **packer dead** | **Y** |
| **size now** | **2,147,651,475** |
| **.part gone** | **Y** |
| **collision 336/337** | **Y — 4 planted AUTOFAB0 records + DC control g0** |
| **next in-circuit mouth** | **ring_fwd @524288** (one bit, then die). Not pub@337. Not genome@0. |

---

## Packer

`DC_WHO_WRITES.md` named HOST_EMIT PID **20656** `python -u muhl_fab_dc.py --write` streaming `.part`.

**PID 20656 is dead.** Sibling claim that it was stopped is true.

A **second** host dump appeared during this verify: PID **3864** `python -u muhl_fab_dc.py --write` started 2026-08-15 01:39:06. Same fabricator. `TARGET_BYTES = 100_000_000_000`. Journal line `dc_fab_write` total 99,999,999,818 against the live 2,147,651,475 computer. `.part` CreationTime 01:39:06; grew to **8,120,843,768** B before kill.

**STOPPED PID 3864.** Removed `muhlnickel_dc.mno.part`. Did not start another dump. `os.replace` did not run. Sealed `.mno` not swapped.

Python left: PID 34508 `MUHL_GO\_byte_read_tmp.py` only (bounded reader, not the packer). No `muhl_fab_dc.py` process.

Do not run `muhl_fab_dc.py --write` again. That path is HOST_EMIT. Off spec for the grow.

---

## One-level `MUHL_DATACENTER`

| object | bytes | LastWriteTime |
|---|---:|---|
| `muhlnickel_dc.mno` | **2,147,651,475** | 2026-08-15T01:38:36.0641170-04:00 |
| `muhlnickel_dc.mno.part` | **absent** | removed this turn |

Seed was 2,147,548,550. AUTOFAB0 append 4117 × 25 = 102,925 → **2,147,651,475**. Header total @184 matches disk. Magic `MUHLDC01`. Pub already fired (`00000001`). Carry `00000000`. fwd@272 and rev@304 packed (256 ones each). EOF−25 = AUTOFAB0 last (`op=00000010` a=3544 b=3545 out=8388791). Planted.

Size not 100 GB. File changing itself (LWT / bits) is normal. Host packer is not how it grows.

---

## Collision (foundry 336/337 = carry/pub)

**Yes.** Plant was no-remap. Foundry operands 336 / 337 **are** this file’s header mouths.

AUTOFAB0 records touching 336 or 337 (4):

| rec | op | a | b | out | hits |
|---:|---:|---:|---:|---:|---|
| 187 | 2 | 334 | 335 | **336** | writes **carry** |
| 188 | 3 | **336** | 129 | 97 | reads **carry** |
| 189 | 4 | 192 | 192 | **337** | writes **pub** |
| 191 | 1 | 34 | **337** | 339 | reads **pub** |

DC control g0 @356: XOR a=303 **b=336** out=272. Carry is already a control operand.

`DATACENTER_100GB.md` planted this on purpose (address collision). **Do not remap** the planted records — that would rewrite live foundry gates after pub already fired. Do not fire pub@337 again (already `00000001`; foundry rec 189 writes that same byte). Do not fire genome@0 (smashes magic).

---

## Next in-circuit mouth

Host = inject + **one bit** + die. File changes itself. N rings, N clocks. No titan. No host 100 GB emit.

**Fire `ring_fwd` @524288** — AUTOFAB0’s named ring, inside this `.mno`, does not sit on carry/pub/magic.

Fallback mouth: aperture table **@8388608** (also inside file, also non-colliding with 336/337).

Button that already died: `dc_foundry_button.py --go` (inject fwd+rev, fire pub@337). That fire is done. Next button addresses **524288**, one bit, exits.

`DC_INCIRCUIT.md` was not on disk to read.
