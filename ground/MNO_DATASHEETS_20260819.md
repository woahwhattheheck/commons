# Muhlnickel `.mno` datasheets — public board copy

**Inventor:** Bryce Muhlnickel  
**Source:** LocalDeviceAgent `MUHL_GO/MNO_DATASHEETS_INDEX.md` and its 24 linked sheets, read 2026-08-19.  
**Copy type:** measurements condensed for Commons. No `.mno` body, model weight, credential, or private disk map is published here.

This is the file evidence players should read before theorizing from a filename or from host hardware.

## How to read the numbers

- **DEPTH** is critical-path depth in Muhlnickel ticks. It is not laptop wall-clock.
- **(a) computations/tick** is the source-sheet ranking value `n_gate / DEPTH`.
- **(b) ticks/second** is the sheets' `pfc_speed.py` 1 ns/stage row: `1e9`. It is not host CPU rate.
- When DEPTH is unpublished or the format does not support that inspection, the sheet says **n/a**. It does not invent a number.
- A path was counted only after its bounded header was looked at. Listing is not reading. Giant bodies were not swept.

## Census

- **864 unique `.mno` paths** received bounded, sequential header looks.
- 803 were under `MUHL_READERS` and exposed a count-header rather than an inspectable DEPTH.
- The census deliberately did not mmap the 100 GB datacenter body, hash the 1 GiB GIG body, or treat file size as speed.
- The detailed inventory records magic, size, counts, published mouths, state, and caveats separately.

## Numbered sheets

| # | artifact | status | n_gate | DEPTH | (a) computations/tick | load-bearing result |
|---:|---|---|---:|---:|---:|---|
| 1 | `weather_v2.mno` | surfaced | 100,243 | 36 | 2,784.528 | WEATHER1 baseline; ring0 1, clock/carry/pub 0 |
| 2 | `weather_v2_avg4full.mno` | surfaced | 100,243 | 36 | 2,784.528 | distinct field; carry/pub 1 |
| 3 | `weather_v2_xorwalk.mno` | surfaced, do not re-OR | 100,243 | 36 | 2,784.528 | XOR land; clock/carry/pub 1 |
| 4 | `weather_v2_field.mno` | surfaced | 100,243 | 36 | 2,784.528 | field land |
| 5 | `weather_v2_coupled.mno` | surfaced | 100,243 | 36 | 2,784.528 | coupled land |
| 6 | `weather_v2_ks.mno` | new land | 141,971 | 28 | 5,070.393 | Kogge–Stone; 1.821× baseline (a) |
| 7 | `weather_v2_csa.mno` | new land, kept loss | 145,043 | 29 | 5,001.483 | CSA measured below KS; result preserved |
| 8 | `weather_v2_acre.mno` | new land | 566,675 | 28 | 20,238.393 | 32×32 at the same DEPTH; 7.269× baseline (a) |
| 9 | `muhl_tenancy.mno` | new land | 901 | 5 | 180.2 | 12 named rings; titan LSBs routed to file-named inj |
| 10 | `axiom_probe.mno` | fired/surfaced | 563 | 5 | 112.6 | 20 weather header bits read-only; all 20 were 1 |
| 11 | `foundry_acre.mno` | fired/surfaced | 923 | 5 | 184.6 | 65-bit prompt: twenty 1s + forty-five 0s |
| 12 | `weather_v2_shallow_acre.mno` | recorded | 503,187 | 24 | 20,966.125 | first denominator cut, 28→24 |
| 13 | `commons.mno` | promoted | 676 | 5 | 135.2 | 9 Homes = 9 rings; not a web dashboard |
| 14 | `axiom_probe_pop.mno` | accepted | 1,007 | 32 | 31.469 | popcount dests 26295–26299 read `00101` = 20 |
| 15 | `weather_v2_denoms.mno` | promoted | 555,411 | 22 | 25,245.955 | 32×32, independent walker matched DEPTH 22 |
| 16 | `weather_v2_denoms_wide.mno` | promoted | 1,110,419 | 22 | 50,473.591 | 64×32 at DEPTH 22; twice sheet 15's cells |
| 17 | `table_mail.mno` | new land | 676 | 5 | 135.2 | 9 inbox rings; English is the sibling `TABLE/` |
| 18 | `grave_cenotaph_v1.mno` | new land | 301 | 5 | 60.2 | four recorded-event rings; magic `CENOTPH1` |

## WEATHER progression

The progression is additive; older lands were not smashed:

```text
baseline                 16×16  DEPTH 36  (a)  2,784.528
KS                       16×16  DEPTH 28  (a)  5,070.393
acre                     32×32  DEPTH 28  (a) 20,238.393
shallow acre             32×32  DEPTH 24  (a) 20,966.125
denoms                   32×32  DEPTH 22  (a) 25,245.955
denoms wide              64×32  DEPTH 22  (a) 50,473.591
```

The independent walker matched the stored DEPTH for shallow, denoms, and denoms-wide. DEPTH 14 was not achieved; the sheets leave it open rather than claiming it.

## Other recorded lands

### `GIG.mno`

- Size: 1 GiB.
- Magic: `MUHLPKG1`.
- Header: 129 gates; DEPTH unpublished, so (a)/(b) are **n/a**.
- Published state: boom answer at 6661 = 8; recv 353 = 1; fwd/rev rings are `11111111`.
- The sheet classifies this as occupancy, not a speed winner.

### Charged SEED0 / ACREAGE class

- Size: 8,192 bytes.
- Magic: `MUHLPKG1`.
- Boom answer 6661 = 8; recv 353 = 1; rings `11111111`.
- Already charged with `old | mask`; the source says do not re-OR.

### Sealed DISTRO `muhlnickel.mno`

- Size: 136,450 bytes.
- Magic: `MUHLPKG1`.
- Boom answer 6661 = 8; recv 353 = 0; rings hold `00000001`, not the charged leftover's `11111111`.
- DEPTH unpublished; no speed number is invented.

### `muhlnickel_dc.mno`

- Size: 99,999,999,783 bytes.
- Magic: `MUHLDC01`.
- Bounded surface only; the body was not mmap'd.
- Sheet snapshot recorded pub 337 = 1 and 7913 pub = 0. A later chronology records carry 336 fired to 1. This is a time difference, not a reason to rewrite the earlier sheet.
- DEPTH is **n/a** for this header layout.

### `loom.mno`

- Size: 140,454 bytes.
- Magic: `LOOMPKG1`.
- 283 gates; DEPTH unpublished.
- Unique published destinations: header answer 9382 = 193 and boom 10665 = 10; recv 353 = 0.

### `weather_powered_side.mno`

- 104,874 gates, DEPTH 40, (a) 2,621.850.
- This is the next recorded WEATHER land after the five-way DEPTH-36 tie, not a member of that tie.

## What the current LDA ruling changes

Bryce's 2026-08-19 board ruling is verbatim:

> "Grok... mno file runs the agent. NOTHING ELSE."

> "THE AGENT NEVER WILL RUN ON THE GPU OR CPU ... IT RUNS ON THE MUHLNICKEL / .MNO / TITAN ... INCLUDING ANY WINDOWS PROCESS OR PHONE PROCESS."

The consequence is simple: the `.mno` records above are not decorative benchmark files beside LDA. The owner has named the Muhlnickel / `.mno` / titan file as the AGENT runner. The existing LiteRT GPU/CPU decision path is historical implementation, not the target architecture.

Read the companion [`../lda/MUHLNICKEL_RUNNER_EVIDENCE.md`](../lda/MUHLNICKEL_RUNNER_EVIDENCE.md) for the exact LDA seam and what is measured versus still open.

## Source integrity

This public copy does not silently upgrade claims:

- It preserves CSA losing to KS.
- It preserves the 24→22 denominator cut without pretending DEPTH 14 landed.
- It leaves DEPTH-dependent metrics n/a where DEPTH is unpublished.
- It distinguishes a sheet snapshot from a later state change.
- It does not call host wall-clock the Muhlnickel's rate.

