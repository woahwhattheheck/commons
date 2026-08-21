# WEATHER AVG4 VERIFY — MISS 008, report is not bytes

**Inventor:** Bryce Muhlnickel. **Seat:** SPEC DADDY GROK.
**When:** 2026-08-16. Button: `WEATHER\muhl_avg4_verify.py`. Die.

Host = surface ∨ die. Dests FROM THIS FILE header.
No 337. No titan. No wipe. No 100k walk. No smash.
One-step integer ref is fab-time verify, not runtime.

Do not promote `WEATHER_AVG4_FULL.md`. This file is the surface.

Σ:WEATHER_AVG4_VERIFY
avg4full sha **a9b8c5d9… MATCH**
genesis **weather.mno @98** ones **671**
int-ref ones **891**
file 500 ones **891**
file 2548 ones **891**
match **Y**
4921 is adder **Y**
leftover 4837 writers 0 **Y**
verdict **BYTE_EXACT_VS_INT**
vaults_smashed **NO**

---

## 0. HASH + SURFACE FROM FILE

`[local]\WEATHER\weather_v2_avg4full.mno`
size **2606416**  magic `WEATHER1`
+8 HIS `n_in/n_wire/n_gate/n_out` = **2048 / 100244 / 100243 / 2048**
+44 QWORDS wire **96** cell_base **500** next_base **2548**
ring0 **104**  gate_base **100340**  stride **25**

| | |
|---|---|
| sha claimed | `a9b8c5d9bcda93c797326ab71cfbcc6046610df5940c61d4e346b464f07b6072` |
| sha FROM FILE | **`a9b8c5d9bcda93c797326ab71cfbcc6046610df5940c61d4e346b464f07b6072` MATCH** |
| field @500 ones | **891 / 2048** |
| NEXT @2548 ones | **891 / 2048** |

---

## 1. GENESIS VAULT (STAT ones, pick 671, do not smash)

| file | cell_base | ones | smash |
|---|---:|---:|---|
| **weather.mno** | **98** | **671 / 2048** | NO — picked |
| weather_v2.mno | 500 | 671 / 2048 | NO |
| weather_v2_coupled.mno | 500 | 671 / 2048 | NO |
| weather_v2_field.mno | 500 | 671 / 2048 | NO |

Picked first 671: `weather.mno` @98. sha `d8a8fc668c57a09c882a3e1c23a1015f6901a556ddb46f5e2a90ca2d62c619cb`.
Kite nine `0xFF` in rows 6–9 cols 6–9: **True**. Plane + kite = 671.

avg4full itself is **not** a genesis vault (500 already 891). Not used as genesis.

---

## 2. INDEPENDENT INTEGER ONE-STEP

16×16 torus. 8-bit cells, one-bit-per-byte, LSB. For each of 256 cells:

`cell' = (N + S + E + W) >> 2`  then `& 0xFF`

Genesis loaded from `weather.mno` @98. Host does this once as fab-time verify. Not a 100k ripple.

| | ones / 2048 | cell-miss vs int / 256 |
|---|---:|---:|
| genesis | **671** | — |
| int-ref | **891** | — |
| avg4full @500 | **891** | **0** |
| avg4full @2548 | **891** | **0** |

match **Y**. Cell-for-cell: file 500 == file 2548 == int-ref.

---

## 3. rec325 AND(4921,168)→2548

FROM FILE:

| rec | organ | |
|---|---|---|
| **325** | AND(**4921**, **168**)→**2548** | next writer cell0 bit0, gated by NW carry |
| **333** | AND(**4837**, **4837**)→**4921** | identity off leftover dest 4837 |
| **241** | NAND(4835, 4836)→**4837** | FA internal |

Cell0 bit0 N/S/E/W dests at `cell_base=500`: **2420 / 628 / 508 / 620**.

Walk producers of 4921 (records only, 108 dests):

- hits **12** field dests
- includes all four NSEW0: **508, 620, 628, 2420**
- one no-writer dest: **96** (const0, adder pad)

4921 is the adder sum in RECORDS. It feeds from N/S/E/W dests at cell_base. Not a dark temp.

leftover 4837 refs: rec241, rec333 only.
avg4 writers still on 4837: **0**. leftover 4837 writers 0 **Y**.

---

## 4. VERDICT

**BYTE_EXACT_VS_INT**

Not promoted from the prior report. Measured this button: hash match, 671 genesis, 891 int-ref, 891@500, 891@2548, 0/256 cell-miss both planes, 4921 adder Y, 4837 writers 0 Y.

337 NO · titan NO · wipe NO · vaults unsmashed · host_ripple_100k NO

path: `[local]\LocalDeviceAgent\MUHL_GO\WEATHER_AVG4_VERIFY.md`
button dies
