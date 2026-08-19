# .mno DATASHEETS — 2026-08-17 player fulfillment

**Inventor:** Bryce Muhlnickel. Click these. Newest-on-top this hour.

## TABLE MAIL (2026-08-17) — inboxes, new land, commons not smashed

| # | file | (a) cpt | DEPTH | n_gate | note |
|---|---|---:|---:|---:|---|
| 17 | [MNO_DS_17_table_mail.md](MNO_DS_17_table_mail.md) | 135.2 | 5 | 676 | 9 inboxes. Board `TABLE\BOARD.md`. Kite/Axiom NEED_BRYCE. |

## TEAM STONE (2026-08-17) — denominator cut #2 + wide blessing, PROMOTED (Gravekeeper RULING 001)

Independent walker `WEATHER\muhl_walk_weather1_depth.py` matched header DEPTH on shallow, denoms, and denoms_wide. Format card `WEATHER\WEATHER1_FORMAT.md` — Gravekeeper authors the readback. Did not smash acre / shallow_acre / v2.

| # | file | (a) cpt | DEPTH | n_gate | vs acre |
|---|---|---:|---:|---:|---|
| 16 | [MNO_DS_16_weather_v2_denoms_wide.md](MNO_DS_16_weather_v2_denoms_wide.md) | **50473.591** | **22** | 1110419 | **2.494×** (64×32 at DEPTH 22) |
| 15 | [MNO_DS_15_weather_v2_denoms.md](MNO_DS_15_weather_v2_denoms.md) | **25245.955** | **22** | 555411 | **1.247×** (P=A\|B prefix, 32×32) |
| 12 | [MNO_DS_12_weather_v2_shallow_acre.md](MNO_DS_12_weather_v2_shallow_acre.md) | **20966.125** | **24** | 503187 | **1.036×** (DEPTH 28→24) |

Did not hit 28→14 (~40k). NAND2 XOR is DEPTH 3; two nested 8-bit adds stay serial.

## KITE (2026-08-17) — Commons is the file

| # | file | (a) cpt | DEPTH | n_gate | note |
|---|---|---:|---:|---:|---|
| 13 | [MNO_DS_13_commons.md](MNO_DS_13_commons.md) | 135.2 | 5 | 676 | 9 Homes = 9 rings. Not a dashboard. |

## AXIOM (2026-08-17) — popcount at named dests

| # | file | (a) cpt | DEPTH | n_gate | note |
|---|---|---:|---:|---:|---|
| 14 | [MNO_DS_14_axiom_probe_pop.md](MNO_DS_14_axiom_probe_pop.md) | 31.469 | 32 | 1007 | pop dests 26295–26299 = count **20** |

Chimera ARDR→EAL already in titan. Remaining three earlier: sheets 9–11.

## AXIOM ASKS — finished in-spec (not as written)

Chimera ARDR→EAL already in titan. Remaining three: new land, dest FROM FILE, no 100GB mmap.

| # | file | (a) cpt | DEPTH | n_gate | ask |
|---|---|---:|---:|---:|---|
| 9 | [MNO_DS_9_tenancy.md](MNO_DS_9_tenancy.md) | 180.2 | 5 | 901 | 12-organ tenancy (not host-copy into dc) |
| 10 | [MNO_DS_10_axiom_probe.md](MNO_DS_10_axiom_probe.md) | 112.6 | 5 | 563 | telemetry (not Python seek organ) |
| 11 | [MNO_DS_11_foundry_acre.md](MNO_DS_11_foundry_acre.md) | 184.6 | 5 | 923 | foundry acre + phys 65-bit inject (not dc loop) |

## NEW LAND (this seat — beat the census winners)

PASS-3 prefix/CSA + occupy-disk acre. Fab `WEATHER\muhl_fab_weather_shallow.py`. Fire `muhl_fire_weather1.py`. Did not smash `weather_v2.mno`.

| # | file | (a) cpt | DEPTH | n_gate | vs v2 |
|---|---|---:|---:|---:|---|
| 8 | [MNO_DS_8_weather_v2_acre.md](MNO_DS_8_weather_v2_acre.md) | **20238.393** | 28 | 566675 | **7.269×** |
| 6 | [MNO_DS_6_weather_v2_ks.md](MNO_DS_6_weather_v2_ks.md) | **5070.393** | 28 | 141971 | **1.821×** |
| 7 | [MNO_DS_7_weather_v2_csa.md](MNO_DS_7_weather_v2_csa.md) | 5001.483 | 29 | 145043 | 1.796× (lost to KS) |

(b) still **1e9** on all three. Rank = (a). CSA named in spec; measured worse than KS on this avg4.

Census **864** unique `.mno` looked at (header ≤224 B each, sequential). Listing ≠ looking. Full dump: `MUHL_GO\MNO_CENSUS_SURFACE.txt`.

No `.mno` in repo `LocalDeviceAgent` body or `C:\llm` this walk. `__pycache__` skipped. dc/GIG: mouths/header only.

## RANKING RULE

1. **(a) computations/tick** = `n_gate / DEPTH` from the FILE + `pfc_speed.py` wavefront mean.
2. **(b) ticks/second** = `1/τ` at `pfc_speed.py` labeled **1 ns/stage** = **1e9**. Not host CPU. Not host wall-clock as the rate.
3. **(b) tied** on every file where DEPTH is published. **more compute per second** = (a)×(b) = same order as (a). No third metric as winner.
4. Top (a) is a **7-file tie** at **2784.528** (all WEATHER v2 DEPTH 36). Five distinct lands of that tie are the 5 sheets. `avg4` (not full) and `xorwalk_COPY` same (a)(b) — not extra-scored.

**BRYCE:**

> we dont optimize for anything besides more compute per second thats the only metric
>
> maybe compute per tick is better

## 5 WINNERS (tie on (a) and (b))

| # | file | (a) cpt | (b) ticks/s | ones |
|---|---|---:|---:|---:|
| 1 | [MNO_DS_1_weather_v2.md](MNO_DS_1_weather_v2.md) | 2784.528 | 1e9 | 2408977 |
| 2 | [MNO_DS_2_weather_v2_avg4full.md](MNO_DS_2_weather_v2_avg4full.md) | 2784.528 | 1e9 | 2410349 |
| 3 | [MNO_DS_3_weather_v2_xorwalk.md](MNO_DS_3_weather_v2_xorwalk.md) | 2784.528 | 1e9 | 2410711 |
| 4 | [MNO_DS_4_weather_v2_field.md](MNO_DS_4_weather_v2_field.md) | 2784.528 | 1e9 | 2380533 |
| 5 | [MNO_DS_5_weather_v2_coupled.md](MNO_DS_5_weather_v2_coupled.md) | 2784.528 | 1e9 | 2378677 |

Next (a) not in the 5: `weather_powered_side` **2621.850**. Then v1 class **116.603**.

## EXTRAS (unique thing the top 5 do not capture)

| sheet | why |
|---|---|
| [MNO_DS_X_weather_powered_side.md](MNO_DS_X_weather_powered_side.md) | unique n_gate 104874 / DEPTH 40 |
| [MNO_DS_X_GIG.md](MNO_DS_X_GIG.md) | occupancy-not-speed · 1 GiB · dest 8 · rings ff |
| [MNO_DS_X_sealed_136450.md](MNO_DS_X_sealed_136450.md) | sealed DISTRO · dest 8 · rings 01 · ones 330988 |
| [MNO_DS_X_dc.md](MNO_DS_X_dc.md) | MUHLDC01 mouths · 100GB · no mmap |
| [MNO_DS_X_loom.md](MNO_DS_X_loom.md) | unique dest 9382 / 10665 |
| [MNO_DS_X_SEED0_charged.md](MNO_DS_X_SEED0_charged.md) | leftover charged · do not re-OR |

## CENSUS COUNT

**864** unique paths. Top folders:

| n | folder |
|---:|---|
| 803 | `Desktop\MUHL_READERS` (looked: magic `\x03\x00…` count-header, not inspect DEPTH) |
| 17 | `Desktop\MUHL_VISIBLE` |
| 15 | `Desktop\MUHLNICKEL_DISTRO` |
| 5 | `Desktop\MUHLNICKEL_DISTRO\CONTAINERS` |
| 11 | `Desktop\WEATHER` |
| 13 | other (APERTURE, DC, HANDOFF copies, LOOM×4, PROBE, ROOKERY, INVENTION_BURST, MODEL_SELECTOR) |

`muhl_cli.py slots` → 5 CONTAINERS. `pfc_speed.py life` → DEPTH 15 / wavefront 18022 (method, not an `.mno`).

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · 10-wide **NO** · re-OR leftovers **NO**
