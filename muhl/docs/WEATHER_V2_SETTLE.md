# WEATHER V2 SETTLE

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16.
Host = inject ∨ surface ∨ die. Dest from the file. No 337. No titan. No wipe.

His words (`BRYCE_WORDS_PC.md`): address is a WRITE — if the bit did not change, you did not address a signal. Shared address is the wire. Host shoots one electron into the ring, then removes itself. 1→1 on rails is not a new address. Do not re-OR fwd/rev. CLAUDE.md: addressed read of the answer IS the computation. Both are his.

He asked whether sending one HAS to be a write. Not answered here.

---

## LIVE (v2 vault — not smashed)

| | |
|---|---|
| file | `[local]\WEATHER\weather_v2.mno` |
| sha256 | **cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d MATCH** |
| size | 2606416 |
| field dest | **500** |
| field ones | **671** (unchanged) |
| next bank | 0/2048 |
| electron | fwd0=rev0=**1** on all six |
| carry / pub / clock | **0 / 0 / 000000** |

NW 104/136/168/169 · NE 170/202/234/235 · SW 236/268/300/301 · SE 302/334/366/367 · GROWTH 368/400/432/433 · WITNESS 434/466/498/499. All from this file.

Rails not re-ORed. 1→1 is not a new address.

---

## BYTE MISS (given — not re-litigated)

Enable AND(fwd[0],rev[0]) is lit on the rails. Mux/avg4 outs did not land in the field. XOR-rotate did not walk. Kite still nine `11111111`. Live field == `SURFACE_V2_DARK.txt` 0/256 diffs.

Rails-lit is not done.

---

## BYTE CHECK — shared address is the wire

Do AND / enable / avg4 **INPUT** addrs equal the ring dests 104/136/…?

### Carry AND — YES (inputs)

| rec | op | a | b | out |
|---|---|---|---|---|
| 99904 | AND | **104** | **136** | 168 |
| 99971 | AND | **170** | **202** | 234 |
| 100038 | AND | **236** | **268** | 300 |
| 100105 | AND | **302** | **334** | 366 |
| 100172 | AND | **368** | **400** | 432 |
| 100239 | AND | **434** | **466** | 498 |

a,b **are** the ring dests. Electron is on those AND inputs. Carry out is 168… still **0**. That bit did not change — carry was not addressed.

### Enable AND — inputs YES, out NO

256 records: AND(104,136)→**87796** and kin (87845, 87894, 87943…).  
a,b equal the ring dests. **out is a different number.** Not a ring dest.

### Mux / avg4 enable readers — NO (v2)

4096 records read those temps. Sample:

| rec | v2 a,b | ring dest? |
|---|---|---|
| 85249 | 87796, 87796 | **NO** |
| 85251 | 87796, 2548 | **NO** (2548 = next_base) |

Field writers 2048: inputs **87802…** — 0 share a ring dest.  
Next writers 2048: inputs **4837…** — 0 share a ring dest.

**The electron is on 104/136. It is not on 87796. Shared address is not the wire from the ring to mux/avg4.**

---

## PATCH — `weather_v2_coupled.mno` (v2 not smashed)

Button: `WEATHER\muhl_couple_weather_v2.py`. Copy v2 records. Do not delete gates. Retarget every reader of the 256 enable-AND temps: that input addr becomes the **fwd dest from the file** (104 / 170 / 236 / 302). Rails / field / carry bytes copied as they lay. No re-OR. No carry write. No host nxt.

| | |
|---|---|
| coupled | `[local]\WEATHER\weather_v2_coupled.mno` |
| sha256 | **6cc69c32ec8050e75dbc5172e1224e00806d9f543c79bf173653e5db8c746a1d** |
| v2 after | cc2775fd… **MATCH** (smashed **NO**) |
| reader inputs retargeted | **6144** (4096 records; NAND(s,s) hits a and b) |
| those records now share a ring dest | **4096 / 4096** |
| still on temp | **0** |

Sample after patch:

| rec | v2 | coupled | share |
|---|---|---|---|
| 85249 | 87796, 87796 | **104, 104** | YES |
| 85251 | 87796, 2548 | **104, 2548** | YES |

Coupled live bits same as v2: electron still fwd0/rev0=1. Carry still 0. Field ones still 671. Header+rails+field byte-exact vs v2. Only gate-record a/b changed.

---

## VERDICT

**v2: STILL_RAILS_ONLY** — miss measured: mux/avg4 input addrs are temps, not 104/136/….

**coupled: records share the ring dests.** Electron is now on those mux/enable inputs (same numbers as fwd0). Carry bit still 0. Field bit still 671. No rail re-OR. No invented dest. No 337. No titan.

337 NO · titan written NO · v2 smashed NO · `--inject` NO
