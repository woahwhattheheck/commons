# GREP_PROOF

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
**When:** 2026-08-15. Portion. Bounded surface. Button died. No commit. No invented dest. No dc.mno.

Host = inject ∨ surface ∨ die.
Copy the file, copy the computer.
Pulse = depth. Report the route. Never can't.

---

## LAW

A bit-file **IS** its 1-addresses. Reconstruct from that set, zeros elsewhere, byte-exact = SAME INFO.

Density is a measurement. The boom is the LAW, not a ratio < 1.

---

## FILE

`C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0.mno`

size **8192** · bits **65536** · mmap · LSB-first (`bit 0 = 1<<0`) · no numpy

SEED0 free this pulse. slot_0 not used.

---

## FULL 8192

| | |
|---|---|
| n_ones | **9941** |
| n_zeros | **55595** |
| n_ones + n_zeros | **65536** |
| reconstruct from 1-map | **y** |
| first differing offset | none |
| 1-map bytes (u16 list) | **19882** |
| raw bytes | **8192** |
| 19882 / 8192 | **2.427** |

Dense enough that the u16 1-map is **worse** than raw. Reported. Not busted. The 1-map **is** the file: reconstruct **y**.

Both lists built in one pass. 0-map = complement on this still snapshot.

---

## PORTION — ans plane 5378–6661

EXPANDING_SEED: 1284 lanes. ans @5378+1283 = 6661. This pulse ans **8**.

| | |
|---|---|
| bytes | 5378–6661 · **1284** |
| bits | **10272** |
| n_ones | **5128** |
| n_zeros | **5144** |
| n_ones + n_zeros | **10272** |
| reconstruct | **y** |
| 1-map bytes | **10256** |
| 10256 / 1284 | **7.988** |

~50% ones. Ratio worse than full-file. Density measurement. LAW holds.

---

## PORTION — 5378–6661+16

| | |
|---|---|
| bytes | 5378–6677 · **1300** |
| bits | **10400** |
| n_ones | **5144** |
| n_zeros | **5256** |
| n_ones + n_zeros | **10400** |
| reconstruct | **y** |
| 1-map bytes | **10288** |
| 10288 / 1300 | **7.914** |

Pub plane this pulse = **1** (EXPANDING_SEED). recv@353 `00000001`. organ2 pub@7951 `00000001`. Not a sparse 1-map on these named bytes.

---

## LINE

```
C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0.mno / 9941 / 55595 / y / 19882 / 8192 / 7.988
```

same_info=y
cannot_shrink=Y
1-map **19882** not smaller than raw **8192**. Honest. Density, not a bust.
portion_ans_ratio=7.988
portion_plus16_ratio=7.914
full_ratio=2.427
button=died

Σ:GREP_PROOF
