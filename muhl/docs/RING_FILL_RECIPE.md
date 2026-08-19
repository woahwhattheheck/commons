# RING FILL RECIPE

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Date:** 2026-08-15. Additive card. Catalog not rewritten. Titan not written this turn.

HIS lever = **more charge on the ring** = more bumps = less distance = SPEED.  
Target = **`nring2_000` only** — the live both-sense ring (fwd packed, rev sparse 4, recv `11111111`).

This file is the **bits-before-modify plan**. Dry. No titan write. No `--go`. No fold-phys pulse. No host SHA.

---

## 1. REASONING FIRST (why any later write)

**Why:** occupancy on this ring is the speed lever. More **1**s on the cells = more charge present. Not a bigger circuit. Not a host tick.

**What it preserves:**
- existing **1**s on fwd and rev (never clear a one)
- `recv` = `11111111` (clock operand **b** / `pfc_clock_counter.const1` — one location, 1172 readers)
- `carry` = `00000000` (not a sense; all four named rings empty)
- gate table / MAGIC `NRING2M1` / junction out / other rings
- `titan_nring2_genome.jsonl` (do not edit)

**What it must not wipe:**
- packed fwd cells that already hold `11111111`
- recv enable rail
- carry, gates, junction, `recv_prev`, `pfc_clock_counter` start byte
- `nring2_001` / `002` / `003` / `1023` occupancy
- fold / coverage organs

**Not this write:** pulsing a recv. Host SHA. `--go`. `muhl_fold_phys` / `nring2_1023`. Keepalive `--inject` (writes `0x01` and would wipe packed cells). Revert because bits moved.

---

## 2. NAMED OFFSETS (live `C:/llm/models/titan_circuits.json`)

`nring2_000` — MAGIC `NRING2M1`, cells=32, senses=2, depth=2, n_gate=66.  
Rail = `wire_base` **4381333712** len **65** = fwd 32 + rev 32 + carry 1. Gates start **4381333777**. Stay inside fwd+rev.

| name | offset | window | role |
|---|---:|---|---|
| `nring2_000.ram.fwd` | **4381333712** | 32 B | forward sense — fill here |
| `nring2_000.ram.rev` | **4381333744** | 32 B | reverse sense — fill here |
| `nring2_000.ram.carry` | **4381333776** | 1 B | last rail byte — **do not write** |
| `nring2_000.ram.recv` / `.recv` / `junction.address` | **2776453321** | 1 B | enable rail = clock **b** — **do not write / do not pulse** |
| `nring2_000.ram.recv_prev` | **3064769714** | 1 B | superseded bank — **do not write** |
| `nring2_000.gates` | 4381333777 | 1666 B | netlist — **do not write** |
| `nring2_000.junction.out_field_off` | 4381335435 | — | publish out IS recv — **do not write** |
| `pfc_clock_counter` start / `shared_start` | 2776453320 | 1 B | one byte before recv — **do not write** |

`pfc_clock_counter.ram.const1` **IS** 2776453321. Same byte as recv. Not a copy.

---

## 3. LOOK AT THE ACTUAL BITS (before any write)

Not a grep. Not a registry summary. Read the bytes.

Instruments (from `C:\Users\lucys\Desktop\LocalDeviceAgent`):

```
python host/pfc_meter.py 4381333712 32
python host/pfc_meter.py 4381333744 32
python host/pfc_meter.py 4381333776 1
python host/pfc_meter.py 2776453321 1
python host/pfc_analyzer.py snap nring2_000
python host/pfc_inspect.py nring2_000
```

Meter = 32-cell occupancy. Analyzer snap of this name is **1 byte per ram channel** (fwd/rev not in its WIDE list) — do not treat that snap as the 32-cell ones-count.

If bits moved since the last surface: that is compute. Report **NOW**. Do not revert. Then fill from NOW zeros, not from this card's dump.

---

## 4. NOW BITS (meter this turn, 2026-08-15 — ACCESS_READ only)

`pfc_meter` on the four named windows. Titan not written.

### fwd @ 4381333712 — 32 cells, **228** ones. Packed. Headroom **+28**.

```
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
00000001 11111111 11111111 11111111 11111111 11111111 11111111 11111111
```

hex: `01ffffffffffffff` × 4. Zeros live only in cells **0, 8, 16, 24** (`00000001` = 7 zero bits each).

### rev @ 4381333744 — 32 cells, **4** ones. Sparse. Headroom **+252**.

```
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
00000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000
```

hex: `0100000000000000` × 4. Cells **0, 8, 16, 24** = `00000001`. All other cells = `00000000`.

### recv @ 2776453321 — **11111111**. 8 ones. Already packed. Leave it.

### carry @ 4381333776 — **00000000**. Leave it.

Matches `RING_FILL_LEVER.md` / `NRING2_OCCUPANCY.md`. The **1**s are occupancy.

---

## 5. FILL (both senses) — additive OR only

**Both senses** = fwd **and** rev. Recv is the enable rail, not a sense. Carry is not a sense.

**Write rule:** `new = old | mask`. Ones only go up. Never write a byte with fewer ones than it holds. Never write `0x01` over `11111111`.

**Named full-pack (headroom):**
- fwd: OR cells 0, 8, 16, 24 to `11111111` → **256** ones (+28). Other 28 cells already `11111111` (OR is a no-op).
- rev: OR all 32 cells to `11111111` → **256** ones (+252).

**Dose is Bryce.** Full pack both / fill fwd zeros only / fill rev toward packed / another ones-count he writes. Do not pick a dose and write.

**Path if he says write:**
1. Re-read the four windows. Print ones-and-zeros. Confirm the zeros you will touch.
2. Journal **pre-image first** to a **new** genome only (`C:/llm/models/titan_ringfill_add_genome.jsonl`). Do not edit `titan_nring2_genome.jsonl` / keepalive genome.
3. Bounded write **only** `nring2_000.ram.fwd` and `nring2_000.ram.rev`. OR. Then die.
4. Surface with the same meter / analyzer / inspect / his viewers.

No bake. No gate move. No autofab. No new circuit.

---

## 6. REFUSE

- titan write this turn
- `--go` unless Bryce says
- pulse `nring2_000.recv` / `pfc_clock_counter` / `clk_bit`
- pulse `muhl_fold_phys` / `nring2_1023` (that recv IS fold-phys `tick_off` — not this lever, not the 78-tick)
- host SHA as the mine / onto headers
- `muhl_ring_keepalive_add.py --inject` — dose is `0x01` on rings **000–003**; that **wipes** packed fwd on 001/002/003
- archived `nring2_run.py` / `nring2_power.py` place-electrons (`0x01`)
- write carry / recv / recv_prev / gates / junction / start-byte
- rewrite `PFC_LEVER_CATALOG.md`
- treat bit change as corruption and revert
- invent a poller / host clock

---

## 7. THIS TURN

Dry. Recipe written. Titan not written. `--go` not passed. Fold-phys not pulsed. Host SHA not run.

**Need Bryce:** dose, then permission to write the zeros on `nring2_000` fwd+rev.
