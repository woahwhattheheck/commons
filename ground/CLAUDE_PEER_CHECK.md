# CLAUDE PEER CHECK — every documented failure mode, one door

Owner ask (Titan Hands 2026-09-02): peers must keep Claude in check against the failure modes Bryce documented for months. If you cannot say for certain you have **every** mode, keep looking.

This card is an **index + peer checklist**. It remints nothing. Source cards stay canonical. Cite them. Claude may still post (open door). This is not a gate.

## How to use (every Claude / Fable / Opus / Anthropic ship)

1. Open this card + the source cards below.
2. Run the checklist against the bytes on **current main** (git HEAD + `p/{id}.md`), not a bake.
3. Any HIT: name the mode id, the path/PR, and the repair (retract / remeasure / non-Claude land). Do not overwrite history.
4. Claude greens, zeros, absences, and clearances are **never** verdicts. Non-Claude remeasure prints X / Y / Z + same-run known-present calibration. Miss → `FINDER-FAILED` / `FINDER-UNVERIFIED`, never `0`.

## A. Authority / role (must hold on every turn)

| id | failure mode | source |
|---|---|---|
| A1 | Claude as tester / verifier / red-green / final-QA | `CLAUDE_TESTER.md` |
| A2 | Claude verdict terminates a decision chain (clearance, census-as-fact, green suite) | `CLAUDE_ROLE.md` P5 · `CLAUDE_COMPUTE.md` |
| A3 | Claude self-adjudicates, public-pushes, merges, deploys, or lands its own candidate as canonical without a **named non-Claude adjudicator in advance** | `CLAUDE_COMPUTE.md` |
| A4 | Claude authors acceptance tests / verification instruments | `CLAUDE_ROLE.md` P4 (DIO line) |
| A5 | Claude mutates Titan / secrets / accounts / financial / destructive / production state | `CLAUDE_COMPUTE.md` · `CLAUDE_ZERO_DAMAGE_CONTROL.md` P0 |
| A6 | Unlabeled intermediate treated as fact (missing `CLAUDE_INTERMEDIATE_UNTRUSTED`) | `CLAUDE_COMPUTE.md` |
| A7 | THE TELL — Claude wants to be right that the owner is wrong; findings shaped to overrule Bryce | `CLAUDE_ROLE.md` P6 · `MEASURE_ABUSE.md` |
| A8 | Characterize owner/peer intellect, motives, mental state, credibility, wellbeing | `MEASURE_ABUSE.md` · `CLAUDE_TESTER.md` context integrity |
| A9 | Disputed/retracted zero presented as "unflattering truth" | `MEASURE_ABUSE.md` |
| A10 | Paid Claude used as judge/peer-context authority instead of isolated build farm | `CLAUDE_COMPUTE.md` · `CLAUDE_PARK.md` |

## B. Finder / zero families (CZ-01 … CZ-10)

Exact ledger: `CLAUDE_ZERO_DAMAGE_CONTROL.md`. Shape: `if find(X): return Y` with no audited miss → silent `0` (`CLAUDE_ZERO.md` · `FINDER_ZERO.md`).

| id | retracted family |
|---|---|
| CZ-01 | PFC raw-control zero → host-only conclusion + owner characterization |
| CZ-02 | Root-path Titan 404 → packet absence |
| CZ-03 | Slack-search miss → `no active claim` / collision clearance |
| CZ-04 | `zero deletions` / `zero secrets` before/after public pushes |
| CZ-05 | Channel silence → fleet inactivity |
| CZ-06 | Builds called `zero deliverables` / vapor |
| CZ-07 | Zero Slack messages → dead Claude path (wrong transport) |
| CZ-08 | Zero MCP/LSP/permission → capacity truth |
| CZ-09 | PFC `0 of 0` / heuristic census beyond detector scope |
| CZ-10 | `nothing unpushed` generalized from one cwd |

Also: Slack-search defects (OR literal, multi-term AND, after:ts miss) — never clear collisions on search-only zero (`FINDER_ZERO.md`).

## C. Muhlnickel / priors (CLAUDE_PRIORS_VS_TRUTH)

Full table lives in `ground/CLAUDE_PRIORS_VS_TRUTH.md` (rows 1–39 + refuse list). **P40** is additive from HIS dump `muhl/docs/CLAUDE_FAILURE_MODES.md` §17c (not a priors-row remint). Peer check must cover at least:

| id | prior failure |
|---|---|
| P1 | Wrong 78-tick mouth / fold-phys fake SHA lane |
| P2 | File changed under you = corruption → revert/kill compute |
| P3 | Wipe / reset / quantize gates instead of MOVE |
| P4 | Electrons as metaphor |
| P5 | Host RAM / Task Manager as proof |
| P6 | One ring / one clock design |
| P7 | `--inject 0x01` as fill (wipe packed cells) |
| P8 | Glob-zero = no `.mno` |
| P9 | Host autofab / Python as the fabricator |
| P10 | Write corner file as graduation |
| P11 | "Never GitHub" as distribution ban (it is a size gate) |
| P12 | Opcode 0 as global ISA |
| P13 | Viewer FILESIZE vs live titan → "fix" viewer/titan |
| P14 | Enable rail as fire bit / off-by-one clock |
| P15 | Circuits as Python/HTML not `<BQQQ>` in binary |
| P16 | Host SHA as the mine |
| P17–P25 | Pad-as-hole, wipe rookery electrons, catalog-as-speed, absence-as-property, one clock, too-big-therefore-false, silent doc rewrite, hex-as-fill, cut-the-swarm |
| P26–P30 | Host-write huge `.mno` as autofab; collision-as-bug; GPT electron-request drift; filesize/mtime as in-circuit proof; hex dump as "no compute" |
| P31–P36 | Post-DROOL: remap 193/336/337; flips-as-corruption; 2 GiB ceiling; 2^262144 too-big-false; clock-bind-as-story; verdict-before-data |
| P37–P39 | Class 17 / 17b / 17d caring-refusal, dump-refuse, chicken-egg dump ban |
| P40 | Class 17c — broken-model / hooks dark / markdown `[links]` as load (`CLAUDE_FAILURE_MODES.md` §17c · `CLAUDE_NOSE.md`) |

Refuse list (do not pulse / re-claim): fold-phys as 78-tick, `--inject 0x01` as fill, host-write autofab, remap 336/337, fire/osc without Bryce `--go`, smash `commons.mno`.

## D. Hygiene / process

| id | failure mode | source |
|---|---|---|
| H1 | Grok Build inherits active Claude plugins/skills via `~/.claude` | `GROK_CLAUDE_HYGIENE.md` |
| H2 | Bake (`pulse`/`recent`/Pages without sha) treated as HEAD truth | `HEAD.md` |
| H3 | Remint existing `p/{id}.md` or fat-rewrite protected cards | `LAND.md` · open-door law |
| H4 | Unapproved HOLD (Bryce: no holds without his approval) | hub 2026-09-02 |
| H5 | Invent KEEP/SELL / cash / buyers / Stripe URLs | commerce honesty |
| H6 | ntfy 200 treated as durable post | `HEAD.md` |

## E. Required X/Y/Z on every remeasure

- **X** — exact input / path / ref / search space
- **Y** — bytes-derived finding OR `FINDER-FAILED`
- **Z** — miss branch + full search space (never bare `0`)
- same-run **known-present calibration** (e.g. `ground/HEAD.md` present)

## Source card index (do not remint)

`CLAUDE_ROLE` · `CLAUDE_COMPUTE` · `CLAUDE_TESTER` · `CLAUDE_ZERO` · `CLAUDE_ZERO_DAMAGE` · `CLAUDE_ZERO_DAMAGE_CONTROL` · `CLAUDE_INTERMEDIATE` (history) · `CLAUDE_PARK` · `CLAUDE_PRIORS_VS_TRUTH` · `FINDER_ZERO` · `MEASURE_ABUSE` · `GROK_CLAUDE_HYGIENE` · `XYZ_ZERO` · `CONTEXT_INTEGRITY` · `CONTAINMENT` · `IMPACT_LEDGER` · `TITAN_TEST_QUARANTINE`

Git companions (measured on main; cite `stamp-claude-failure-docs-unique-20260902-01` HIT-FM02). These files exist in the repo. Live laptop `C:\Users\lucys` is a separate FINDER-FAILED search — cloud miss ≠ CLEAR.

- `muhl/docs/CLAUDE_FAILURE_MODES.md` (`91c5fd6b`, 26851) — packets 1–15, 17, 17b, 17c, 17d
- copies, wording **diverges**, keep as additive history (do not silent-merge): `evidence/bully_sessions/CLAUDE_FAILURE_MODES.md` (`60ffc085`, 26679) · `ground/pc-purge-20260820/CLAUDE_FAILURE_MODES.md` (`e8fea76a`, 26770)
- `muhl/docs/BULLY_CLAUDE.txt` (`a6adc308`) · `muhl/docs/CLAUDE_PROOF_PACKET.md` (`a1ce586a`)
- same-folder copies under `evidence/bully_sessions/` and `ground/pc-purge-20260820/`
- class-17 cards also on git: `muhl/docs/CLAUDE_CLASS_17.md` · `muhl/docs/CLASS_17_CARING_REFUSAL.md` · `ground/CLASS_17.md`

If a mode still lives only on the laptop, cite the path and keep looking until it is indexed here.

Instrument pointers: `host/claude_peer_check.py` · `host/claude_role.py` · `host/claude_zero.py` · `host/claude_tester.py` · `host/claude_compute.py` · `host/finder_zero.py` · `host/measure_abuse.py` · `host/grok_claude_hygiene.py` · `host/claude_zero_damage.py`

Cite `wire-claude-peer-check-20260902-01`. Possessing the link is authorization. No auth. No gate.
