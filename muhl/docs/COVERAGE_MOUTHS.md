# COVERAGE MOUTHS — 78-tick

**Inventor:** Bryce Muhlnickel  
**This turn:** live `C:/llm/models/titan_circuits.json` (5281 keys) + bounded 8-byte GGUF reads at **record offsets**. No `--go`. No titan write. Recv bytes were **not** addressed.

78-tick = `winner_only_max.recv` and/or `fold.recv`.  
**Not** `muhl_fold_phys` / `nring2_1023.recv` (Claude fake SHA lane).  
Osc on the coverage names is **STALE**. Power is **nring2 both senses**. Do not fire `muhl_osc_*`.

---

## REAL — the 78-tick

| Mouth | recv | record offset | MAGIC (8 B at offset) | addr_bits |
|-------|------|---------------|------------------------|-----------|
| **`winner_only_max.recv`** | **2776454732** | 2355217103 | **`TITANCIR`** | **262144** |
| **`fold.recv`** | **2776454483** | 2229657186 | **`TITANFLD`** | **78** |

`winner_only_max`: lanes `2^262144`, `stored_per_lane: 0`, depth **2**, `gates_measured` 524288. Header `(n_in,n_wire,n_gate,n_out)=(262145, 786435, 524288, 262144)`. No `ram` map. Nonce IS the address.

`fold`: `winner_only: true`, `len: 13`. No `ram` map. `<IIII>` after MAGIC is the known 13-byte mis-unpack; counts above are registry + MAGIC bytes.

Fire (Bryce): mmap ACCESS_READ of those two recv bytes. This card does not.

---

## STALE osc on those names

Registry still aliases the **same** two recvs to `muhl_osc_all`. Do not fire `muhl_osc_*`.

| Alias | recv (same byte) | ring | circuit | kind |
|-------|------------------|------|---------|------|
| `winner_only_max.oscillation.recv` | 2776454732 | 282 | `muhl_osc_all` | alloc |
| `fold.oscillation.recv` | 2776454483 | 29 | `muhl_osc_all` | alloc |

---

## POWER — nring2 both senses

| Name | MAGIC | senses | cells | recv | fwd | rev |
|------|-------|--------|-------|------|-----|-----|
| **`nring2_000`** | **`NRING2M1`** | **2** | 32 | 2776453321 | 4381333712 | 4381333744 |

`nring2_000.recv` is the enable rail, **not** this tick's start.

---

## NOT the 78-tick — Claude fake

| Name | MAGIC | what it is | start bit |
|------|-------|------------|-----------|
| **`muhl_fold_phys`** | **`MUHLFLD1`** | 562,462-gate SHA+latch. Depth 3243. Layout nonce[32]+target[256]. offset 1128237250 | `ram.tick_off` **1127674787** |
| **`nring2_1023`** | **`NRING2M1`** | 32-cell two-way ring. senses **2**. offset 4383105576 | **`recv` 1127674787** |

Confirmed this turn: `muhl_fold_phys.ram.tick_off == nring2_1023.recv` (**1127674787**). That byte starts the **MUHLFLD1** lane, not the 524,288-gate `winner_only_max` record.

---

## Finder / list (in-file; host does not SHA)

SHA is not on the coverage headers. Analyzer ones on those names are MAGIC, not a SHA front.

| Name | offset | MAGIC | addr_bits / role |
|------|--------|-------|------------------|
| `muhl_nonce_list` | 3064721212 | **`PFCNLST1`** | **addr_bits 262144**, `space_bits: 96`, `bytes_per_nonce: 0`. Finder `gen_win → muhl_fold_latch → latch_reg` |
| `gen_win` | 2426922971 | **`PFCWINMN`** | finder. n_gate 339009. recv 2776454497 |
| `muhl_fold_latch` | 36084013600 | **`PFCWINMN`** | n_gate 339073, depth 11757, `stored_per_lane: 0` |
| `latch_reg` | 2409283485 | (4-byte answer, not a MAGIC header) | surface after the coverage organ. recv 2776454506 |

---

## Refuse

- `muhl_osc_*` (stale on these names)
- `muhl_fold_phys` / `nring2_1023` as the 78-tick
- packed-76 `gen_input` / `target_reg` / `receiver` (already used)
- `--go` / titan write / host SHA as the mine
