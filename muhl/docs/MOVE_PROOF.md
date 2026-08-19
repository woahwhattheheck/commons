# MOVE_PROOF

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Scratch only. Sealed DISTRO not opened for write. dc.mno not injected. Titan not opened. No fire 337. No remap 336/337. No 7913. No numpy. No `--inject 0x01`. No commit. Button died.

Host = inject ∨ surface ∨ die. Address IS the wiring. Collision out==in is the wire. Never delete gates, only MOVE them.

---

## Scratch

| | |
|---|---|
| **path** | `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0_MOVE.mno` |
| **from** | copy of `SEED0.mno` |
| **size before** | **8192** |
| **size after** | **8431** |

Sealed `muhlnickel.mno` / `muhlnickel_dc.mno` / `titan.gguf` not written.

---

## Record layout (read, not guessed)

`<BQQQ>` = op:u8 · a:u64 · b:u64 · out:u64. Package-local file offsets. DISTRO opcodes XOR=0 AND=1 OR=3.

Header-named tables (untouched): ring@503 ×66 · net@2153 ×129. Live adder mouths 288/320/352/353/354/370/5378. Not moved.

Organ 2 (EXPANDING_SEED + `muhl_seed0_mirror_button.py` fab, then read on this scratch):

| span | what |
|---|---|
| 7946–7951 | wires fwd/rev/carry/pub |
| 7952–7959 | collision occupancy |
| 7960–8109 | 6 × 25 ring |
| 8110–8184 | 3 × 25 collision |

Records read before move — match fab:

```
ring0  XOR 7947 7950 → 7946
ring1  XOR 7946 7950 → 7947
ring2  XOR 7949 7950 → 7948
ring3  XOR 7948 7950 → 7949
ring4  AND 7946 7948 → 7950
ring5  OR  7951 7950 → 7951
col0   OR  7952 7953 → 7954
col1   OR  7954 7955 → 7954
col2   OR  7954 7951 → 7956
```

col0.out == col1.in == **7954**. Adder ring+net pointers into [7946,8185): **0**.

---

## Control

`python host/muhl_cli.py surface SEED0_MOVE.mno 6661 1`  
**before = 8** `00001000`

---

## In-file MOVE

Region **7946–8184** (239 B) occupied at EOF **8192**. delta = **246**.  
Every a/b/out in the nine moved records +246. Wire bytes moved with them. Old span vacated (MOVE, not copy). Header `total` 8192 → 8431. 336/337/7913/353/288/320/370/ans plane not remapped.

```
ring0  XOR 8193 8196 → 8192
ring1  XOR 8192 8196 → 8193
ring2  XOR 8195 8196 → 8194
ring3  XOR 8194 8196 → 8195
ring4  AND 8192 8194 → 8196
ring5  OR  8197 8196 → 8197
col0   OR  8198 8199 → 8200
col1   OR  8200 8201 → 8200
col2   OR  8200 8197 → 8202
```

col0.out == col1.in == **8200**.

---

## After

`python host/muhl_cli.py surface SEED0_MOVE.mno 6661 1`  
**after = 8** `00001000`

336 stayed **1**. 337 stayed **1**. 7913 stayed **1**.

---

## Σ

```
C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0_MOVE.mno / 8 / 8 / n / y / NO
```

| field | |
|---|---|
| scratch_path | `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0_MOVE.mno` |
| before | **8** |
| after | **8** |
| broke | **n** |
| in_file_move | **y** |
| remapped_336 | **NO** |

Button died.
