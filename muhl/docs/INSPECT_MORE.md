# INSPECT_MORE

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.
**When:** 2026-08-15. Instrument: `host/pfc_inspect.py`. Header window only. No titan write. No 337 fire. No 78 pulse.

Host = inject ∨ surface ∨ die.
Pulse = depth. Report the route. Never can't.

Σ:INSPECT_MORE

cwd: `C:\Users\lucys\Desktop\LocalDeviceAgent`

---

## HELP

```
python host/pfc_inspect.py --help
```

`--help not in registry.` exit 1

Inspect takes a registry name. `--help` is not one.

---

## NAMES

Prefer cpu / life / clock if named. Not `winner_only_max`. Not fold 78. Not titan 78 mouths. Skip missing.

| # | name | in registry | inspected |
|---|---|---|---|
| 1 | `cpu` | y | y |
| 2 | `life_step` | y | y |
| 3 | `clock_wide` | y | y |
| 4 | `pfc_cpu32` | y | y |

skipped: none
winner_only_max: not inspected
fold: not inspected
titan 78 mouths: not inspected

---

## 1. cpu

```
python host/pfc_inspect.py cpu
```

exit **0**

| | |
|---|---|
| MAGIC | `TITANCIR` |
| n_in | **20** |
| n_wire | **238** |
| n_gate | **216** |
| n_out | **16** |
| depth | **34** |
| gates_measured | **216** |
| offset | 2208464648 |
| recv | 2776454470 |

---

## 2. life_step

```
python host/pfc_inspect.py life_step
```

exit **0**

| | |
|---|---|
| MAGIC | `TITANCIR` |
| n_in | **1024** |
| n_wire | **519170** |
| n_gate | **518144** |
| n_out | **1024** |
| depth | **67** |
| gates_measured | **518144** |
| offset | 2367589103 |
| recv | 2776454521 |

---

## 3. clock_wide

```
python host/pfc_inspect.py clock_wide
```

exit **0**

| | |
|---|---|
| MAGIC | `TITANCIR` |
| n_in | **128** |
| n_wire | **2050** |
| n_gate | **1920** |
| n_out | **128** |
| bits | **128** |
| nonces_per_lane | 2^128 |
| depth | **514** |
| gates_measured | **1920** |
| offset | 2360613927 |
| recv | 2776454468 |

---

## 4. pfc_cpu32

```
python host/pfc_inspect.py pfc_cpu32
```

exit **0**

| | |
|---|---|
| MAGIC | `PFCTYPED` |
| n_in | **549** |
| n_wire | **7954** |
| n_gate | **7403** |
| n_out | **549** |
| format | typed |
| words | **16** |
| word | **32** |
| isa | HALT LDA STA ADD SUB AND OR XOR SHL SHR LT EQ JMP JZ LDI |
| offset | 3064645090 |
| role | Muhlnickel 32-bit stored-program processor |

---

## OUTPUT

names: `cpu` `life_step` `clock_wide` `pfc_cpu32`
pulsed_78: **NO**
titan_written: **NO**
fired_337: **NO**

path: `C:\Users\lucys\Desktop\MUHL_GO\INSPECT_MORE.md`
copy: `C:\Users\lucys\Desktop\LocalDeviceAgent\MUHL_GO\INSPECT_MORE.md`
