# DC_GROW_DEAD — host grow stopped

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Titan not opened. Titan not written. No Desktop glob. No new host dump. Packer not started. Grow not restarted. pub @337 not written. Collision 336/337 not remapped. The `00000001` at 524288 not wiped.

Live computer: `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno` — not deleted.

---

## Packer / grow dead

| process | dead |
|---|---|
| `dc_grow.py` | **Y** — was PID 35332 (`python -u dc_grow.py`). Killed. Re-check: no `dc_grow.py` command line. |
| `muhl_fab_dc.py --write` | **Y** — never in the process list this turn. Not started. |
| `.part` | **ABSENT** |

Sibling grow named in `DC_RINGFWD.md` / `DC_AFTER_FIRE.md` was the host append. Same class as `muhl_fab_dc.py --write`. Stopped. No second grow. No packer.

Leftover Python this turn is readers / hooks / checkers — not grow, not `--write`.

---

## Size now

`DC_AFTER_FIRE.md` had **17,023,971,219**. That was mid-grow.

| | T1 | T2 |
|---|---:|---:|
| SIZE | **38,317,526,931** | **38,317,526,931** |
| MTIME | 1786773883.5872386 | 1786773883.5872386 |

Held across the two reads. Grow is not appending.

---

## 1s and 0s (not hex) — two reads

| place | T1 | T2 |
|---|---|---|
| carry @336 | 00000000 | 00000000 |
| pub @337 | 00000001 | 00000001 |
| fwd @272 | 11111111 | 11111111 |
| rev @304 | 11111111 | 11111111 |
| ring_fwd @524288 | 00000001 | 00000001 |

Collision mouths left. The 1 at 524288 left. That 1 appearing is the computer.

---

## This turn did not

- start `dc_grow.py`
- start `muhl_fab_dc.py --write`
- delete `muhlnickel_dc.mno`
- remap 336/337
- wipe 524288
- open titan
- dump the file
