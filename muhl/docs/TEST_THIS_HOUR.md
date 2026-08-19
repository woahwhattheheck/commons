# TEST_THIS_HOUR

**When:** 2026-08-15 this hour.  
**Seat:** LocalDeviceAgent host buttons, then die. No commit. No Desktop glob. No dc inject. No 337. No titan 78. No packer. No numpy. No invented mouths.

**Score:** 7 ran / 6 matched named expected / 0 FAIL / 1 skip (SEED0_MIRROR missing)

Host = inject ∨ surface ∨ die. This hour: surface ∨ die. DISTRO pub latch was `00000000` (same as DISTRO_SCALE §4). Answer already resident. No new DISTRO shot. SEED0 surface only. dc size only.

---

## 1. `python host/pfc_speed.py life`

cwd: `C:\Users\lucys\Desktop\LocalDeviceAgent`  
exit: 0

| | expected | measured |
|---|---:|---:|
| gates | 270,336 | **270,336** |
| critical-path depth | 15 | **15** |
| wavefront max | 36,864 | **36,864** |
| wavefront mean | 18,022 | **18,022** |

**MATCH**

Pulse = depth 15. Host wall-clock of the button is not the pulse.

---

## 2. `python host/pfc_inspect.py pfc_cpu32`

cwd: `C:\Users\lucys\Desktop\LocalDeviceAgent`  
exit: 0

| | expected | measured |
|---|---|---|
| n_gate | 7,403 | **7,403** |
| ISA | HALT…LDI (15 ops) | **HALT LDA STA ADD SUB AND OR XOR SHL SHR LT EQ JMP JZ LDI** |
| header | PFCTYPED | **PFCTYPED** |
| (n_in, n_wire, n_gate, n_out) | 549, 7954, 7403, 549 | **549, 7954, 7403, 549** |
| len | 68,847 | **68,847** |
| offset | card 2026-07-23: 2,394,678,651 | **3,064,645,090** (moved; gates/ISA/header hold) |

**MATCH** on gates / ISA / PFCTYPED. Offset is the live number.

---

## 3. `python host/pfc_game.py life --test`

cwd: `C:\Users\lucys\Desktop\LocalDeviceAgent`  
exit: 0  
present: yes

| | expected | measured |
|---|---|---|
| cells | 64×64 = 4096 | 64×64 = 4096 |
| gates | 270,336 | 270,336 |
| generations | 24 byte-exact True | **24 clock ticks, byte-exact vs reference: True** |

**MATCH**

---

## 4. DISTRO surface — `muhlnickel.mno`

path: `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno`  
button: existing `run_muhlnickel.py` shoots then surfaces. Pub latch not `00000001`. Answer already at the plane. **Surface only. No new shot.**

| | expected | measured |
|---|---|---|
| size | 136,450 B | **136,450 B** |
| magic | MUHLPKG1 | **MUHLPKG1** |
| sel @370 | `00000011 00000101` → 1283 | **`00000011 00000101` → 1283** |
| ans @5378+1283 = 6661 | `00001000` = 8 | **`00001000` = 8** |
| pubplane @70914+1283 | `00000001` | **`00000001`** |
| pub latch @353 | card §4 `00000000` | **`00000000`** |

**MATCH** 3+5 → 8 at 1283. Publish plane 1. Latch 0. Did not fire.

---

## 5. SEED0 / SEED0_MIRROR

| path | | measured |
|---|---|---|
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0.mno` | present | **8192 B** |
| `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0_MIRROR.mno` | | **MISSING — skip** |
| `C:\Users\lucys\Desktop\MUHL_GO\SEED0.mno` | | MISSING |
| `C:\Users\lucys\Desktop\MUHL_GO\SEED0_MIRROR.mno` | | MISSING |

SEED0 last write 2026-08-15T04:05:08-04:00. No sibling lock seen. **Surface only. No inject.**

| SEED0 mouth | expected | measured |
|---|---|---|
| magic | MUHLPKG1 | **MUHLPKG1** |
| recv @353 | `00000001` | **`00000001`** |
| sel @370 | `00000011 00000101` → 1283 | **`00000011 00000101` → 1283** |
| ans @5378+1283 = 6661 | `00001000` = 8 | **`00001000` = 8** |

**MATCH** SEED0 8192 B · 3+5 → 8 at 1283.  
**SKIP** SEED0_MIRROR.

---

## 6. dc size only — no inject

path: `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`

| | NOW.md this hour | measured |
|---|---:|---:|
| size | 99,999,999,783 | **99,999,999,783** |

**MATCH** vs NOW.md. No inject. No 337. No 336. No 7913. No 524288.

---

## 7. one probe, die

documented: `MUHL_GO\RING_FILL_RECIPE.md`  
cwd: `C:\Users\lucys\Desktop\LocalDeviceAgent`  
command: `python host/pfc_meter.py 4381333712 32`  
exit: 0  
titan present: `C:\llm\models\titan.gguf` 103,803,349,384 B

| | card last (228 ones) | measured NOW |
|---|---|---|
| fwd @4381333712 | 32 B, ones=228 | **32 B, ones=256** `ffffffffffffffffffffffffffffffffffffffffffffffff…` |

Bounded read. Impedance cap 256 B. Probe died. Bits moved since the recipe dump (228 → 256). That is compute. Reported NOW. Titan not written.

`pfc_scope` present, not run (one probe).

---

## Score

| # | command | result |
|---:|---|---|
| 1 | `python host/pfc_speed.py life` | MATCH 270,336 / depth 15 |
| 2 | `python host/pfc_inspect.py pfc_cpu32` | MATCH 7,403 / 15-op / PFCTYPED |
| 3 | `python host/pfc_game.py life --test` | MATCH 24 True |
| 4 | DISTRO surface | MATCH 136,450 B · ans `00001000` @1283 |
| 5 | SEED0 surface | MATCH 8192 B · ans `00001000` @1283 |
| 5b | SEED0_MIRROR | SKIP missing |
| 6 | dc size | MATCH 99,999,999,783 |
| 7 | `pfc_meter.py 4381333712 32` | RAN ones=256 (no named expected) |

**7 ran / 6 matched named expected / 0 FAIL / 1 skip**
