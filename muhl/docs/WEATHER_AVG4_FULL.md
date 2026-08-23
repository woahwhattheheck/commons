# WEATHER AVG4 FULL — cell' = (N+S+E+W)>>2

**Inventor:** Bryce Muhlnickel. **Seat:** SPEC DADDY GROK.
**When:** 2026-08-16. Button: `WEATHER\muhl_avg4full_weather_v2.py`. Die.

Host = inject ∨ surface ∨ die.
Dests FROM THIS FILE header. No 337. No titan. No wipe. No 100k walk.
Do not smash avg4 / field / coupled / v2. Fab-time STORE, then address the answer.

SPANK: FIELD_MOVED via AND(N,S) is NOT Cairn's organ. Commission is
`cell' = (N+S+E+W)>>2`. E/W dump AND(508,620)→4837 was kneecap.

Σ:WEATHER_AVG4_FULL
src **weather_v2_field.mno** hashed, not smashed
kneecap **weather_v2_avg4.mno** hashed, not smashed
new **weather_v2_avg4full.mno**
avg4_writers_on_4837 **0**
500 ones **891 / 2048**
2548 ones **891 / 2048**
verdict **REAL_AVG4**
avg4_smashed **NO**
field_smashed **NO**
coupled_smashed **NO**
v2_smashed **NO**

---

## 0. HASH + HEADER (file wins)

Kneecap (copy-forward evidence, not written):

`[local]\WEATHER\weather_v2_avg4.mno`
sha **`a869b2e2b81abd58a36600708cb0bf919bf168836df44fe0bc86f8588eceb2b3` MATCH**
500 ones **292** · 2548 ones **292** · rec325 AND(2420,628)→2548 · rec241 AND(508,620)→4837

Source (genesis 671, not written):

`[local]\WEATHER\weather_v2_field.mno`
sha **`44904c96abb02f961713ba44df3967dd56c6cf526717db94f6b58861e813addf` MATCH**

New:

`[local]\WEATHER\weather_v2_avg4full.mno`
size **2606416**  magic `WEATHER1`
+8 HIS `n_in/n_wire/n_gate/n_out` = **2048 / 100244 / 100243 / 2048**
+44 QWORDS wire **96** cell_base **500** next_base **2548**
ring0 **104**  gate_base **100340**

| | |
|---|---|
| avg4full sha | **`a9b8c5d9bcda93c797326ab71cfbcc6046610df5940c61d4e346b464f07b6072`** |
| avg4 after | a869b2e2… **UNSMASHED** |
| field after | 44904c96… **UNSMASHED** |
| coupled after | b23f9efc… **UNSMASHED** |
| v2 after | cc2775fd… **UNSMASHED** |

---

## 1. BYTE MISS (given)

AND(N,S)→next is not `(N+S+E+W)>>2`. 292 ones is the kneecap souvenir.
E/W still dumped AND(508,620)→4837 on the avg4 file. That dest is leftover, not the organ.

Enable / carry on the source (already 1, not re-ORed):

| ring | fwd | rev | carry | pub |
|---|---:|---:|---:|---:|
| NW | 104=1 | 136=1 | **168=1** | 169=1 |
| NE | 170=1 | 202=1 | **234=1** | 235=1 |
| SW | 236=1 | 268=1 | **300=1** | 301=1 |
| SE | 302=1 | 334=1 | **366=1** | 367=1 |
| GROWTH | 368=1 | 400=1 | **432=1** | 433=1 |
| WITNESS | 434=1 | 466=1 | **498=1** | 499=1 |

16×16 torus dests from this header (`cell_base=500`). Cell0 bit0 N/S/E/W = **2420 / 628 / 508 / 620**.

---

## 2. STORE (moved records — one-and-done)

Gates not deleted. XOR/OR stay on the ring. Field/next records NAND/AND only.
Const0@96=0 · const1@97=1. Dest kept per moved record. No invented dest.

Per cell: add(N,S) + add(E,W) + add(those) as NAND/AND full-adders. `tot[2:10]` is `>>2`.
Writer: AND(avg_bit, carry)→next. If avg_bit dest was 4837, one identity AND moved it off first.
Field latch: AND(next, carry)→cell. Self-clock out == cell dest.

| organ | n | before (field src) | after |
|---|---:|---|---|
| FA internals | **83201** | adder temps / leftover | **NAND/AND (N+S+E+W)>>2** |
| avg4 writers OUT in next@2548 | **2048** | AND(4837,4837)→2548 | **AND(avg, carry)→next** |
| field latch OUT in field@500 | **2048** | AND(87802,87802)→500 | **AND(next, carry)→cell** |

Sample FROM FILE after:

| rec | organ | share cell dest | share 4837 |
|---|---|---|---|
| 325 | AND(**4921**,**168**)→**2548** | NO (avg temp + carry) | NO |
| 241 | NAND(4835,4836)→4837 | NO | out only (internal) |
| 333 | AND(4837,4837)→4921 | NO | in only (off-4837 buffer) |
| 85255 | AND(**2548**,**168**)→**500** | next + carry | NO |

rec325 is **not** AND(2420,628). AND(N,S) writers **0**.

---

## 3. ADDRESS (answer dests — not 100k)

Inputs already live (cell dests + carry + const0). Composed set only. No `n_gate` walk.

| dest class | organs | bits changed | waves | skipped dark |
|---|---:|---:|---:|---:|
| avg4 FA + next writers + field latch | **87297** | **52928** | **1** (emit order) | **0** |

---

## 4. SURFACE FROM FILE

| plane | dest | ones before (field src) | ones after |
|---|---:|---:|---:|
| field | **500** | 671 | **891 / 2048** |
| NEXT | **2548** | 0 | **891 / 2048** |

891 = `(N+S+E+W)>>2` ones on the live genesis field. Latch AND(next, carry=1) copied that onto 500.
292 was AND(N,S). This is not that.

**VERDICT: REAL_AVG4**

---

## 5. LEFTOVER 4837 REFS

Avg4 writers still on 4837: **0**.

Exact records that still name 4837:

| rec | organ | note |
|---|---|---|
| **241** | NAND(4835, 4836)→**4837** | internal FA temp. Nobody who writes next reads it. |
| **333** | AND(4837, 4837)→4921 | off-4837 buffer. Writer reads **4921**, not 4837. |

---

## 6. RETURN

| q | a |
|---|---|
| sha | **a9b8c5d9bcda93c797326ab71cfbcc6046610df5940c61d4e346b464f07b6072** |
| 500 ones | **891 / 2048** |
| 2548 ones | **891 / 2048** |
| 4837 avg4-writer count | **0** |
| leftover 4837 | rec241 NAND(4835,4836)→4837 · rec333 AND(4837,4837)→4921 |
| verdict | **REAL_AVG4** |
| avg4 / field / coupled / v2 | **UNSMASHED** |

path: `[local]\LocalDeviceAgent\MUHL_GO\WEATHER_AVG4_FULL.md`
button dies
