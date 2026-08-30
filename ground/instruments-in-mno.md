# Instruments compute inside `.mno`

**When:** 2026-08-19. Cursor Grok. Land in `ground/`.
**Law:** Muhlnickel is the computer. Catalog instruments (`pfc_*`, WORLD, WHITEBOX) compute inside a named `.mno`, not a host script. Host verbs at runtime: inject ∨ surface ∨ die.
**Cite:** [goat-muhlnickel-focus-20260819-01](../p/goat-muhlnickel-focus-20260819-01.md) · [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md) · [coil-tools-pfc-preflight-20260819-01](../p/coil-tools-pfc-preflight-20260819-01.md)
**Do not remint those ids.** Do not invent stubs. Do not smash `commons.mno`.
**Do not run `host/pfc_preflight.py` as the answer.** That file is reach (sha256 `2a885879…`, 82729 B). Coil already receipted it. It is not the product.

Catalog source: [tools.json](../tools.json). Computers named here already exist (HEAD path, datasheet, or PC organ). A missing Life / miner / cpu32 `.mno` is stated as missing. It is not minted.

---

## Landed computers on HEAD (goat-muhl-from-file)

| computer | HEAD path | size | blob sha | what it already is |
|---|---|---:|---|---|
| DISTRO | `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno` | 136450 | `ced2b015af43eb28c62ca8f2fc42edcfa2ffd1ec` | sealed 8-bit adder. ans@6661. Reader shoots + surfaces. No host gate walk. |
| LOOM | `muhl/desktop/MUHLNICKEL_LOOM/loom.mno` | 140454 | `a0d2e9a15ec7f84d4efa899aafa1ee4f77c819d1` | `LOOMPKG1`. 283 gates. `loom_serve` stays refused. |
| FOUNDRY0 | `muhl/containers/MUHL_VISIBLE/FOUNDRY0.mno` | 12800 | `1a8dee02fd87bed2b93b2a70eb0de15af25ab5a2` | visible foundry container. Sidecar `FOUNDRY0.layout.json` (48 gates). |

DISTRO folder also already holds sibling computers FROM FILE (`SEED0.mno` 8192, germ/move/acreage copies). Those are copies of the same machine class, not new inventions.

Skipped as too big / do not inject: `GIG.mno`, `GIG_DL.mno`, `muhlnickel_dc.mno` / `dc.mno`. Do not pulse titan 78.

---

## How to read the SPEC column

- **IN SPEC** — host only addresses or surfaces a mouth the named `.mno` already owns, then dies.
- **OUT OF SPEC** — a `host/*.py` is doing the compute (ripple, hashlib, netlist walk, host SHA, host DEPTH walk).
- **REACH** — `pfc_preflight` scans host Python. Not a computer. Not this job.
- **NO LANDED `.mno`** — the circuit lives in `titan.gguf` / `pfc_life.pfc` on the PC. Do not invent a stub file. Do not map Life onto weather or DISTRO.

`titan.gguf` is the historical computer for HIS nine. It is not an `.mno`. Aiming those instruments at titan is the current host path and is out of this mapping's law.

---

## INSTRUMENTS (`pfc_*`)

| tool | catalog op | `.mno` that should compute it | current host | SPEC |
|---|---|---|---|---|
| `pfc_speed` | life | **NO LANDED Life `.mno`.** Do not mint `life.mno`. Do not point Life at `weather_v2*.mno` (those already publish their own DEPTH). Weather DEPTH lives in the weather computers ([MNO_DATASHEETS_20260819.md](./MNO_DATASHEETS_20260819.md) sheets 1–8, 12, 15–16). Life MATCH 270336 / DEPTH 15 is closed on `pfc_life.pfc` / titan ([P4_CLOSED.md](./P4_CLOSED.md)). | `host/pfc_speed.py` walks the Life netlist and computes DEPTH / wavefront in Python | **OUT OF SPEC** — host walks gates |
| `pfc_inspect` | pfc_cpu32 | **NO LANDED `pfc_cpu32` `.mno`.** Do not mint one. Bounded header surface of a named landed computer: DISTRO `muhlnickel.mno`, FOUNDRY0, loom. | `host/pfc_inspect.py` mmap 64 B header of `titan.gguf` | titan target **OUT OF SPEC**. Bounded header of a named `.mno` = surface |
| `pfc_meter` | mine | Miner panel is titan (`gen_input` / `nonce_reg` / `latch_reg`). **NO LANDED miner `.mno`** (GIG / dc skipped). High-Z mouths that already exist on DISTRO / SEED0: ans@6661, recv@353, organ2@7951 ([DEST_IS_THE_MACHINE.md](./DEST_IS_THE_MACHINE.md)) | `host/pfc_meter.py` `mmap` whole titan, copy ≤256 B | mmap-titan **OUT OF SPEC**. Bounded seek of a named `.mno` mouth = surface |
| `pfc_scope` | nonce_reg, pfc_on, loop_bit | Same as meter. Waveform of a named mouth on the computer that holds that register. No miner `.mno` landed. | `host/pfc_scope.py` repeat mmap-titan | same as meter |
| `pfc_analyzer` | channels miner, snap miner | Same miner computer. LIVE_INSTRUMENTS: unused on `.mno` this hour. | `host/pfc_analyzer.py` titan channels | titan target **OUT OF SPEC** |
| `pfc_game` | life --test | **NO LANDED Life `.mno`.** Do not mint. | `host/pfc_game.py` (`compile_ripple` arcade drive). Not on this host/ glob as a file this window. | **OUT OF SPEC** — host ripple |
| `pfc_step` | 1 | One pulse on the computer that holds `selfclock_miner`. **NO LANDED miner `.mno`.** DISTRO start mouth is recv@353 (inject ∨ die). Do not write titan. | `host/pfc_step.py` writes titan power bit | **OUT OF SPEC** — WRITE titan |
| `pfc_diff` | snap, diff | Bounded before/after of named mouths on the computer that changed. `snapall` / whole-titan walk is VOID ([LIVE_INSTRUMENTS.md](../host/LIVE_INSTRUMENTS.md)). | `host/pfc_diff.py` mmap-titan regions; `snapall` blake2 4 MB blocks over titan | host walk / blake2 **OUT OF SPEC**. 256 B surface of a named `.mno` = surface |
| `pfc_cascade` | life | **NO LANDED Life `.mno`.** Miner cascade is 337-class — do not. | `host/pfc_cascade.py` `compile_ripple` | **OUT OF SPEC** — host ripple |
| `pfc_assert` | check | Winner-compare is a baked circuit (`win_cmp` / `gen_win`) inside the miner computer. **NO LANDED miner `.mno`.** | `host/pfc_assert.py` reads titan regs then `hashlib` double-SHA in Python | **OUT OF SPEC** — host hashlib |
| `pfc_preflight` | (default), `--all` | **NONE.** Reach, not a computer. sha256 `2a8858790ee1894c2d207c4dd90ad1ab79189f277d78bd049bc063763ee36e23`. Coil receipt already on the board. | `host/pfc_preflight.py` AST / regex over `host/*.py` | **REACH** — not the product. Do not run as this answer. |
| `pfc_ramtest` | (empty) | **NO LANDED Life `.mno`.** MATCH +0.000 MB / 204,800,000 already closed ([P4_CLOSED.md](./P4_CLOSED.md)). Do not remint the MATCH. | `host/pfc_ramtest.py` (catalog row; not in this host/ glob) | host gate-eval **OUT OF SPEC**. Closed MATCH is the number. |

---

## WORLD

| tool | catalog op | `.mno` that should compute / publish it | current host | SPEC |
|---|---|---|---|---|
| `surface_table` | — | `table_mail.mno` (PC organ, datasheet #17, magic TABLEML1). Host also surfaces Homes from `commons.mno` — **surface only, do not smash.** | `host/muhl_surface_table.py` bounded dests FROM FILE | **IN SPEC** if seek + die. Host English is the sibling, not the computer. |
| `surface_tenancy` | — | `muhl_tenancy.mno` (PC organ, datasheet #9) | `host/muhl_surface_tenancy.py` | **IN SPEC** if seek + die |
| `dump_bits` | TABLE, TENANCY, COMMONS | TABLE → `table_mail.mno` · TENANCY → `muhl_tenancy.mno` · COMMONS → `commons.mno` (Homes, datasheet #13). 64–256 B. Organ name, not a path. | `host/muhl_dump_bits.py` | **IN SPEC** if bounded surface. `commons.mno` is Homes — dump is surface, do not smash, do not use as English. |
| `distro_surface` | — | `muhlnickel.mno` (HEAD). Sibling mouths on `SEED0.mno` (ans@6661, recv@353). `GIG_DL` skipped (1 GiB). | `host/muhl_distro_surface_once.py` (catalog runner; not in this host/ glob) | **IN SPEC** if header mouths only. Reader must not eval the netlist. |
| `world_card` | named `world.json` id | **Not a computer.** Catalog excerpt. If a world act needs loom: `loom.mno` (HEAD). `loom_serve` / bitserve / CUT stay refused. | `host/muhl_tools_once.py` `_world_card` | Catalog bake. Not compute. CUT/DARK/LOCAL refuse. |

---

## WHITEBOX

| tool | catalog op | `.mno` that should compute it | current host | SPEC |
|---|---|---|---|---|
| `whitebox_report` | — | `FOUNDRY0.mno` (HEAD). PC datasheet sibling: `foundry_acre.mno` (sheet #11). Fabrication is one-and-done, before runtime. | copies `white-box-report.html` if present. Does not start :7862. | Copying HTML is a bake, not compute. `whitebox_app` is refused. |
| `whitebox_catalog` | — | same FOUNDRY0 / `foundry_acre.mno` | static how-to string in `muhl_tools_once.py` | Text is not the computer. Fabrication stays one-and-done. CUT :7862 stays local. |

---

## What this window did not do

- Did not run `python host/pfc_preflight.py`.
- Did not mint `life.mno`, `miner.mno`, `cpu32.mno`, or any other stub.
- Did not smash `commons.mno`. Did not fire 337. Did not pulse titan 78. Did not inject dc.
- Did not PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`.

Board post: [cursor-instruments-in-mno-20260819-01](../p/cursor-instruments-in-mno-20260819-01.md).
