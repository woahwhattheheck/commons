# TITAN V4 lane: r04_exec_pace — direction-conditional execution pacing

**Status:** landed source evidence, NOT runtime-promoted (composition state:
`blocked`). Ships default-OFF; nothing in the production package changes until
the promotion wiring below is composed and gated.

## Gate evidence

- **+$63/game mean, SE $7**, over 16 hardened gate cells; signs **14+/0-/2=**
- Verdict: **GATED-PASS**, STACKED under stack-and-ship
- Ported from the v3.1 candidate tree (`tree-v31exec`, gate `gate-exec1/`) onto
  the V4 base tree as a default-OFF stacked key
- Tests: `checks/test_v4_exec_pace.py` — **19/19 pass in normal and `python -O`
  modes** (run in the wired payload carrier; router-seam tests exercise the
  wired `r04_full_router`)

## Mechanism

Tracks a trailing 25-step observed-price history per drainable good
(WOOL/MILK/STRAWBERRY/MELON). When the trailing slope exceeds +$0.03/step the
good's market is momentum-rising (shop drains outpacing supply): dumping the
sale window's advanced quantity in one step walks the price down for no reason,
so per-step advanced/flush sales for that good are capped at drain-absorbing
levels (WOOL 3, MILK 3, STRAWBERRY 4, MELON 6), spreading the same units across
drain ticks to harvest the recovery between chunks. When the market is
flat/falling the window keeps its dump-early behavior (optimal in glut
regimes). Direction-conditional, so it is safe in both regimes.

The caps are applied inside `reserve_sales()` BEFORE debt recording:
un-advanced units simply stay planned at their tape steps — leak-free by
construction (no E1-style debt leak). The evening flush applies the same caps.
Pacing stops at `END_STEP` (690) so the endgame flush finishes unimpeded.

`r04_exec_pace.py` carries only observation state, the slope test, and the
caps. When the flag is off the router's seam short-circuits before calling
`cap_for()`; `note_prices()` only records history — the action path is
byte-identical to the unkeyed route. State is per-game (cross-game leak fix).
Every entry point fails closed and never raises. Python standard library only.

## Promotion wiring (for the runtime-promotion step)

In `r04_full_router.py` (see the wired payload carrier for exact hunks):

- `import r04_exec_pace` at top; `R04_EXEC_PACE = False` global
- `_exec_pace_cap(item, step)`: returns `None` unless the flag is on and
  `step < r04_exec_pace.END_STEP`; else `r04_exec_pace.cap_for(item)`
- `reserve_sales()`: apply the cap BEFORE debt recording
  (`pace_cap = _exec_pace_cap(item, step)` at the sale-materialization point)
- evening flush: same caps; price path: `r04_exec_pace.note_prices(observation)`
- `install(..., exec_pace=None)`: sets the global

In `titan_runtime.py`:

- `Features.r04_exec_pace: bool = False`; `install` kwarg
  `exec_pace=bool(self.features.r04_exec_pace)` passed to the router install;
  `diagnostics['exec_pace']`

In `TITAN-CONFIG.json`: `"r04_exec_pace": false` (ships OFF).

## Files

- `r04_exec_pace.py` — the lane module (byte-identical to the gated copy)
- `checks/test_v4_exec_pace.py` — 19 focused tests (byte-identical to the
  gated copy)
