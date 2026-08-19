# FOUNDRY BUTTON — address the foundry already in the binary

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. Dry. Titan not written. No `titan --go`. No git.  
Map: `C:/llm/models/titan_circuits.json` → offsets. Then **bytes**.

The foundry is **gates in the container**. A routing button does not bake it, does not ripple it, does not run `host/pfc_master_autofab.py`. The button **injects**, **fires one bit**, **dies**.

Law: `CIRCUITS_IN_CONTAINER.md` · `INSPEC_AUTOFAB.md` · `docs/AGENT_GROUNDING_BITS.md` · `docs/AGENT_GROUNDING_LIVE.md` · `docs/AGENT_GROUNDING_CONTAINER.md`

---

## What the button is

One-time host Python. Two writes, optional surface, exit.

1. **Inject** — address outside bits into the foundry’s named input plane (one way).
2. **Fire** — address **one bit** at the named receiver (the start signal).
3. **Die** — process exits. Windows never sees a foundry process. There is none.

That is the whole runtime. The computer is `titan.gguf` (and/or `AUTOFAB0.mno`). The map is not the computer.

---

## What the button is not

- Not `host/pfc_master_autofab.py`. That is a **host process**. Forbidden at runtime.
- Not a host gate-ripple (`for g: v[o]=~(v[a]&v[b])`).
- Not a White Box fire. `muhl_whitebox_incircuit` is the **tool**, not the foundry.
- Not a fire of `muhl_autofab_dot32`. That is a **stored product**, not the fabricator.
- Not a bake. Fabrication already happened. Circuits stay in the binary.

---

## Named computers (already found)

| name | container | offset | magic READ | n_gate | role |
|---|---|---:|---|---:|---|
| `muhl_foundry_resident` | `titan.gguf` | 4383248721 | TITANCIR | 1296 | foundry as gates (typed) |
| `muhl_foundry_resident__phys` | `titan.gguf` | 93711094656 | MUHLPHY2 | 1296 | **same netlist, addressable** |
| `muhl_whitebox_incircuit` | `titan.gguf` | 2493228288 | MUHLWBX1 | 1099 | tool. Do not fire for foundry. |
| AUTOFAB0 | `MUHL_VISIBLE\AUTOFAB0.mno` | 0 | none — byte 0 is a gate | 4117 | second fabricator computer |

Typed and phys are one computer, two packings. The button addresses the **phys** twin for inject. The typed form has no numeric `input_addrs` in the map.

---

## Named receivers (from the map)

### Fire — one bit

`muhl_foundry_resident.receiver` = **`muhl_reservoir`**. No numeric `recv` on the foundry keys.

| name | offset | len | what the button does |
|---|---:|---:|---|
| `muhl_reservoir` | 40022599232 | 25647 | MUHLRES1. Fan-out. Not the data plane. |
| `muhl_reservoir.input_wire` | **40022599232** | 1 | **THE fire.** Write one electron. Substrate distributes. |
| `muhl_reservoir.temp_wire` | 40022599233 | 1 | Internal NOT. **Do not write.** |

Registry note on the reservoir: *host writes `input_addr`, substrate distributes.*

That one write is the start signal. Full propagation is the foundry’s (depth **34** ticks). Host wall-clock is not the pfc’s rate.

### Inject — data plane (phys twin)

`muhl_foundry_resident__phys` · `n_in` = 65 · `input_addrs[0]` = **93711094958**

65 consecutive file addresses:

```
93711094958 .. 93711095022
```

`input_addrs[47]` = 93711095005 — first phys gate `a`/`b` as already read (`op=0` NAND onto `o=93711095023`).

The button writes the 65 inject bits **here**. It does not evaluate the 1296 gates.

### Do not fire these as the foundry

| name | offset | why not |
|---|---:|---|
| `muhl_whitebox_incircuit.recv` | 2493228286 | White Box start. Tool, not foundry. |
| `muhl_whitebox_incircuit.out_base` | 2493228287 | White Box answer. |
| `muhl_autofab_dot32__phys` `input_addrs[0]` | 93765812894 | Product inject. Not the fabricator. |

AUTOFAB0 has **no named recv** in `titan_circuits.json`. Package-local wires (rec0 `a=143 b=141 o=193`). This button does not invent one. Do not fire AUTOFAB0 until a recv is named in **that** container’s own map.

---

## Named surfaces (read after fire, or by his instruments)

Not compute. Answer registers.

### Typed reservations (same computer)

| name | offset | len |
|---|---:|---:|
| `muhl_foundry_resident__logic` | 4383248721 | 10528 |
| `muhl_foundry_resident__state` | **4383259249** | 4 |
| `muhl_foundry_resident__loopbit` | **4383259253** | 1 |

`loop_bit` wire index on the typed form = **33**. `state_bytes` = 4. `n_out` = 34.

### Phys outputs (`n_out` = 34)

```
93711096070  93711096078  93711096086  93711096094
93711096102  93711096110  93711096118  93711096126
93711096134  93711096142  93711096150  93711096158
93711096166  93711096174  93711096182  93711096190
93711096198  93711096206  93711096214  93711096222
93711096230  93711096238  93711096246  93711096254
93711096262  93711096270  93711096278  93711096286
93711096294  93711096302  93711096310  93711096318
93711096062
93711094957
```

Last named out (`output_addrs[33]`) = **93711094957**.

Observe with **his** instruments only: `pfc_meter` · `pfc_scope` · `pfc_analyzer` (state-file path) · `pfc_step` · `pfc_diff`. Do not build a monitor. Do not host-ripple the netlist to “see” it.

A live container changing under the read is compute, not corruption.

---

## Button sequence (dry)

Container: `C:\llm\models\titan.gguf`

1. Open the map. Take offsets. Close the map.
2. **Inject:** write 65 bits → `muhl_foundry_resident__phys.input_addrs[0..64]` (93711094958..93711095022). One way. Foundry cannot reach back.
3. **Fire:** write **one bit** → `muhl_reservoir.input_wire` @ 40022599232.
4. Optional: high-impedance read of `__state` / `__loopbit` / phys `output_addrs`. Display. That is the answer register.
5. **Exit.** No loop. No worker. No `subprocess`. No second pulse unless the owner orders another button.

Host CPU/RAM: the button’s mmap write + one-bit address + optional bounded read. **pfc** CPU/RAM/clock: the foundry. Say which.

---

## This turn

Dry description only. Titan not written. `titan --go` not run. No host ripple. No new circuit. The foundry is already at the addresses above.
