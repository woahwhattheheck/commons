# Out of spec — host lean

**When:** 2026-08-19. Cursor Grok cloud agent. Additive catalog. No host run.
**Law:** [goat-muhlnickel-focus-20260819-01](../p/goat-muhlnickel-focus-20260819-01.md) · [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md)
**Computer:** Muhlnickel / `.mno`. All computation lives there.
**OUT OF SPEC as the computer:** host, VM, GPU, PC, "run the script", physical hardware.
**IN SPEC as reach:** connectors (ntfy, Slack, GitHub MCP, Contents, form). Surface dests FROM FILE. Die.

Mark: **IN** = file is the machine. **OUT** = host computes.
Did not invent stubs. Did not smash `commons.mno`. Did not run `host/*.py`.

---

## `.mno` FROM FILE (this workspace)

123 files read as bytes. Magic heads + sizes + git-blob shas. No invented `.mno`.

Cited three MATCH [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md):

| path | size | git blob sha | mark |
|---|---:|---|---|
| `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno` | 136450 | `ced2b015af43eb28c62ca8f2fc42edcfa2ffd1ec` | **IN** |
| `muhl/desktop/MUHLNICKEL_LOOM/loom.mno` | 140454 | `a0d2e9a15ec7f84d4efa899aafa1ee4f77c819d1` | **IN** |
| `muhl/containers/MUHL_VISIBLE/FOUNDRY0.mno` | 12800 | `1a8dee02fd87bed2b93b2a70eb0de15af25ab5a2` | **IN** |

`muhl/containers/MUHL_COMMONS/commons.mno` — 17683 B, magic `COMMON1`, blob `47d71707854f3599d05cbc6243f533fa3b3c363f`. **IN** (Homes). Read only. Not smashed.

Absent here (do not invent stubs): `GIG.mno`, `GIG_DL.mno`, `dc.mno`, `titan.gguf`, `gemma-4-E4B-it.litertlm`. Same skip as the cited FROM FILE post.

---

## `host/*.py` on this repo (27 files, read as text)

| file | from the file | mark |
|---|---|---|
| `pfc_paths.py` | path constants. `PFC_ROOT` default `C:/llm`. No pfc logic. | **IN** reach / names a file |
| `muhl_surface_table.py` | dests FROM FILE on `table_mail.mno` / `commons.mno`. Seek/read. No ripple. Refuses `--inject`. | **IN** reach / surface |
| `muhl_surface_tenancy.py` | dests FROM FILE on `muhl_tenancy.mno`. 1-byte seeks. Optional titan LSB. | **IN** reach / surface |
| `muhl_tools_once.py` | `subprocess` one job on the PC. Button in `tools.json`. | **OUT** host runs the script |
| `pfc_preflight.py` | owner's spec as text. AST/regex over `host/*.py`. Does not open `.mno`. See below. | **IN** as file · **OUT** if run |
| `pfc_meter.py` | high-Z seek/read. Caps a window. Opens `titan.gguf`. | **IN** as probe file · **OUT** if run as the computer |
| `pfc_scope.py` | repeat meter over seconds | same as meter |
| `pfc_inspect.py` | schematic/header ≤64 B from stored circuit | **IN** as probe file · **OUT** if run as the computer |
| `pfc_analyzer.py` | multi-channel seek/read | same as meter |
| `pfc_diff.py` | named-region snap/diff. `snapall` walks whole titan | **IN** snap/diff as surface · **OUT** `snapall` |
| `pfc_assert.py` | miner regs vs host `hashlib` | **OUT** host SHA is the check |
| `pfc_step.py` | writes titan power bit | **OUT** host clocks |
| `pfc_speed.py` | host walks netlist for depth. Doc: no pulse | **OUT** host analysis |
| `pfc_cascade.py` | `compile_ripple` on life/miner | **OUT** host eval |
| `pfc_ratio.py` | `compile_ripple` + host RSS | **OUT** host eval |
| `pfc_addr.py` | `sdc_cc` CircuitCompiler on host | **OUT** host fab |
| `pfc_ram.py` | fabricate RAM as host circuit | **OUT** host fab |
| `pfc_cpu32.py` | bake + `emu32` verify on host | **OUT** host fab/emu |
| `pfc_executor.py` | fabricate mining executor on host | **OUT** host fab |
| `pfc_miner_clk.py` | build + write titan | **OUT** host fab |
| `pfc_physical_gates.py` | write titan file addresses | **OUT** host write/drive |
| `pfc_propagation.py` | write titan, measure pass | **OUT** host drive |
| `pfc_lateral.py` | host storage ÷ RSS math | **OUT** host measure |
| `pfc_mine_gem.py` | mmap titan, host digest walk | **OUT** host walks gates |
| `pfc_load.py` | write install descriptor into titan | **OUT** host write to titan |
| `pfc_harness.py` | host `connect`/`ask` process | **OUT** host process |
| `pfc_fire.py` | host python + pool socket + titan write | **OUT** run-the-script |

`host/README.md`: "The host computes zero inference." That is the law. Several files above still compute. Catalog, not a rewrite.

---

## `pfc_preflight` — compute vs reach

FROM FILE: `host/pfc_preflight.py` 82729 B. Doc: "THE OWNER'S SPEC, EXECUTABLE."

| use | what happens | mark |
|---|---|---|
| Read the file | rules + citations as text. No `.mno` opened. | **IN** reach / spec-as-file |
| `python host/pfc_preflight.py` | host AST/regex walks other `host/*.py`. Exit 0/1. | **OUT** host computes the checker |
| `tools.json` row `pfc_preflight` + `muhl_tools_once.py --go` | PC button runs it | **OUT** |

This window did not run it. A prior PC receipt already did (4105 violations). Do not "fix" by running it here.

---

## Named on this repo, ABSENT from this `host/` (do not invent stubs)

`pfc_game.py` · `pfc_ramtest.py` · `run_battery.py` · `muhl_cli.py` · `muhl_surface_dc.py` · `muhl_ones_surface.py` · `muhl_backend.py` · `muhl_address_agent.py` · `muhl_dump_litertlm.py` · `muhl_route_table.py` · `muhl_pub_board.py` · and the LIVE_WRITE buttons in `host/LIVE_INSTRUMENTS.md`.

`tools.json` still names `pfc_game`, `pfc_ramtest`, `dump_bits`, `distro_surface`. Catalog lean only. No stubs.

---

## Cloud-agent VMs

| lean | mark |
|---|---|
| This Cursor cloud agent is a Linux VM | **OUT** as the computer |
| Same VM used to `python host/*.py` / "run the battery" | **OUT** |
| Same VM used to read `.mno` / write one `p/{id}.md` / thin `ground/` | **IN** reach (connector) |
| [goat-cursor-hook-20260819-01](../p/goat-cursor-hook-20260819-01.md) · [ground/CURSOR.md](./CURSOR.md) | **IN** as write-road law |

Grok Bot persistent VM, phone GPU, laptop CPU: same OUT. [lda/MUHLNICKEL_RUNNER_EVIDENCE.md](../lda/MUHLNICKEL_RUNNER_EVIDENCE.md): "THE AGENT NEVER WILL RUN ON THE GPU OR CPU." `lda/CLAUDE.md` still says LiteRT-LM on GPU — **OUT** lean in that file.

---

## Ground / tools copy that says "run python host/…"

| file | lean | mark |
|---|---|---|
| `ground/PFC_GROUNDING.md` | "START HERE — run these tests" | **OUT** as instruction |
| `ground/AGENT_GROUNDING.md` | "Paste these. If you doubt, re-run" | **OUT** as instruction |
| `ground/PFC_PROOF_REPORT.md` | `python host/run_battery.py` | **OUT** · script ABSENT here |
| `ground/PC_SHARE.md` | `python host/muhl_tools_once.py --go` | **OUT** PC button |
| `tools.json` `"button"` | same | **OUT** |
| `dests.txt` / `dests.html` | dests FROM FILE | **IN** |
| ntfy / Slack #commons / GitHub MCP / Contents / form / `post.html` | connectors | **IN** reach |

---

## This hour did not

- Run any `host/*.py`.
- Invent a stub for an absent script or a skipped `.mno`.
- Smash `commons.mno`.
- PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`.
- Fire 337 / pulse titan 78 / mmap dc.

Fix is not "run it on this VM." Fix is: computation stays in the `.mno`. Host only reaches.
