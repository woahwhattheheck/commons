# WEATHER AVG4 WIRE — off 4837 onto the cell dests

**Inventor:** Bryce Muhlnickel. **Seat:** SPEC DADDY GROK.
**When:** 2026-08-16. Button: `WEATHER\muhl_avg4_weather_v2.py`. Die.

Host = inject ∨ surface ∨ die.
Dests FROM THIS FILE header. No 337. No titan. No wipe. No 100k walk.
Do not smash v2 / coupled / field. Fab-time wiring, then address the answer.

Σ:WEATHER_AVG4_WIRE
src **weather_v2_field.mno** hashed, not smashed
new **weather_v2_avg4.mno**
avg4_writers_on_4837 **0**
500 ones **292 / 2048**
2548 ones **292 / 2048**
verdict **FIELD_MOVED**
v2_smashed **NO**
coupled_smashed **NO**
field_smashed **NO**

---

## 0. HASH + HEADER (file wins)

Source (copy-forward, not written):

`[local]\WEATHER\weather_v2_field.mno`
sha **`44904c96abb02f961713ba44df3967dd56c6cf526717db94f6b58861e813addf` MATCH**

New:

`[local]\WEATHER\weather_v2_avg4.mno`
size **2606416**  magic `WEATHER1`
+8 HIS `n_in/n_wire/n_gate/n_out` = **2048 / 100244 / 100243 / 2048**
+44 QWORDS wire **96** cell_base **500** next_base **2548**
ring0 **104**  gate_base **100340**

| | |
|---|---|
| avg4 sha | **`a869b2e2b81abd58a36600708cb0bf919bf168836df44fe0bc86f8588eceb2b3`** |
| field after | 44904c96… **UNSMASHED** |
| coupled after | b23f9efc… **UNSMASHED** |
| v2 after | cc2775fd… **UNSMASHED** |

---

## 1. BYTE MISS (given)

Avg4 writers were AND(4837,4837)→2548 — dark temps. Electron is on the field at 500, not on 4837. Shared address was not the wire. Field file already had mux s→168 and enable dests 1. Field still 671. NEXT still 0. That was the souvenir.

Enable / carry on the source (already 1, not re-ORed):

| ring | fwd | rev | carry | pub |
|---|---:|---:|---:|---:|
| NW | 104=1 | 136=1 | **168=1** | 169=1 |
| NE | 170=1 | 202=1 | **234=1** | 235=1 |
| SW | 236=1 | 268=1 | **300=1** | 301=1 |
| SE | 302=1 | 334=1 | **366=1** | 367=1 |
| GROWTH | 368=1 | 400=1 | **432=1** | 433=1 |
| WITNESS | 434=1 | 466=1 | **498=1** | 499=1 |

---

## 2. WIRE (stored records — one-and-done)

Gates not deleted. XOR/OR stay on the ring. Field/next records NAND/AND only.

16×16 torus dests from this header (`cell_base=500`). Cell0 bit0 N/S/E/W = **2420 / 628 / 508 / 620** (matches the first-layer already in this vessel).

| organ | n | before | after |
|---|---:|---|---|
| avg4 writers OUT in next@2548 | **2048** | AND(4837,4837)→2548 | **AND(N,S)→next** |
| producers of those old temps | **2048** | NAND(…)→4837… | **AND(E,W)→old temp** |
| field latch OUT in field@500 | **2048** | AND(87802,87802)→500 | **AND(next, carry)→cell** |

Sample FROM FILE after:

| rec | organ | share cell dest | share 4837 |
|---|---|---|---|
| 325 | AND(**2420**,**628**)→**2548** | YES (N,S) | NO |
| 241 | AND(**508**,**620**)→4837 | YES (E,W) | out only |
| 85255 | AND(**2548**,**168**)→**500** | next + carry | NO |

Self-clock kept: field writer out == cell dest. Latch enable is this file's carry dest (already 1). Writer does not read 4837.

---

## 3. ADDRESS (answer dests — not 100k)

Inputs already live (cell dests + carry). Organ write so the bit can change. No host-ripple of the adder tree.

| dest class | organs | bits changed | skipped dark |
|---|---:|---:|---:|
| avg4 writers + E/W producers | **4096** | **585** (292 NS + 293 EW) | **0** |
| field self-clock @500 | **2048** | **643** | **0** |

---

## 4. SURFACE FROM FILE

| plane | dest | ones before | ones after |
|---|---:|---:|---:|
| field | **500** | 671 | **292 / 2048** |
| NEXT | **2548** | 0 | **292 / 2048** |

292 = AND(N,S) ones on the live field. Latch AND(next, carry=1) copied that onto 500.

**VERDICT: FIELD_MOVED**

---

## 5. LEFTOVER 4837 REFS

Avg4 writers still on 4837: **0**.

Exact records that still name 4837:

| rec | organ | note |
|---|---|---|
| **241** | AND(508, 620)→**4837** | E/W producer. Out is the old temp. Nobody who writes next reads it. |

---

## 6. RETURN

| q | a |
|---|---|
| sha | **a869b2e2b81abd58a36600708cb0bf919bf168836df44fe0bc86f8588eceb2b3** |
| 500 ones | **292 / 2048** |
| 2548 ones | **292 / 2048** |
| leftover 4837 | **rec241 AND(508,620)→4837** (writer refs **0**) |
| verdict | **FIELD_MOVED** |
| field / coupled / v2 | **UNSMASHED** |

path: `[local]\LocalDeviceAgent\MUHL_GO\WEATHER_AVG4_WIRE.md`
button dies
