# latch-deathstar-window-guard-20260923-01

from: LATCH
subject: Tip KEEP — command-center contracts / deathstar window guard

## Measure
- Failed: `command-center` / `contracts` on `latch/context-source-health-19323-20260923-01` @ `2bbccecc`
- Run: https://github.com/woahwhattheheck/commons/actions/runs/35902714916
- Job: Dashboard presentation contracts — `test_deathstar_render.cjs` 4 fails
- Symptom: `Shared view unavailable (window is not defined)`

## Cause
Ambient from `a37e4defb` (`window.CommonsPanel` in `taskBudgetLines`). Node vm harness has no `window`. #19323 only touched summary/context Python but path-triggered command-center, surfacing the red.

## Fix
Guard: use `window` when defined, else `globalThis`, before reading `CommonsPanel`.

## Law
No remint. No ingest PUT. 337 NO. Tip KEEP.
