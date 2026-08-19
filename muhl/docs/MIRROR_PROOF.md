# MIRROR PROOF

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Crown build. Twin on disk. No commit. dc.mno not injected. Sealed DISTRO read only. Titan not opened.

Host = inject both senses (`old | mask`) ∨ one bit at recv ∨ surface ∨ die.  
Same topology + same injection = same state.  
Copy the file, copy the computer.

The wire would have carried only the inject bits; the frames/body never travel.

---

## Twin

| | left | right |
|---|---|---|
| **path** | `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0_VIRGIN.mno` | `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0_MIRROR.mno` |
| **size** | **8192** | **8192** |
| **magic** | `MUHLPKG1` | `MUHLPKG1` |
| **ans @5378+1283** | **8** `00001000` | **8** `00001000` |
| **pubplane +1283** | **1** `00000001` | **1** `00000001` |
| **recv @353** | `00000001` | `00000001` |
| **select @370** | 3, 5 → 1283 | 3, 5 → 1283 |

**match y.** Byte-exact. Same sha256 both twins.

Live germ `SEED0.mno` 8192 B left as-is (already shot). Sealed DISTRO `muhlnickel.mno` still **136450** B.

---

## Inject (same mask, both files, both senses)

| mouth | addr | mask |
|---|---:|---|
| fwd | 288 | `00000001 00000001 00000000 00000000 00000000 00000000 00000000 00000000` then `00000001` × 8 (3) |
| rev | 320 | same bits (5 in the high 8) `00000001 00000000 00000001 00000000 00000000 00000000 00000000 00000000` then `00000001` × 16 drive |
| opnd | 354 | those 16 shot bits `old \|` |
| select | 370 | `00000011 00000101` = 3, 5 |
| recv | 353 | `old \| 00000001` |

Law: `new = old | mask`. Ones up. Not `--inject 0x01` wipe.

---

## Latch

SEED0 was already shot 3+5=8. Recv `00000001`. Organ latched — a new OR shot cannot clear those bits.

**latched_had_to_refab y.** Same fab path as the seed builder (READ sealed DISTRO, 8192 B, first 1284 lanes, organ 2 in held bytes). Virgin recv was `00000000`. Same 3+5 shot onto both virgins. Recv `00000000` → `00000001` on both. Surface +1283 = **8** on both.

---

## Button

`host/muhl_seed0_mirror_button.py` — copy ∨ fab-virgin ∨ inject ∨ surface ∨ die.  
No gate-ripple. No dc.mno. No 337. No titan 78.

**button died y.**
