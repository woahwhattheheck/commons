# H3b sheep max-held harvest-priority recovery

Canonical V4 source-custody recovery from PR #12603, kept inside the single `candidates/v4` tree and the existing `repairs/gameplay/h3b-sheep-clip` authority.

## Current source closure

This package now folds the two detached fail-closed successors preserved in the #12603 history into the current V4 ABI:

- required standard configuration must be *observed*: `_standard_configuration()` asks `_cfg(..., _MISSING)` instead of silently substituting expected constants, so `configuration=None` or any missing required field fails closed;
- sheep custody is structure-authenticated: `_strict_sheep()` requires both `kind == "PASTURE"` and `animal == "SHEEP"` before H3b may reason about clipping risk.

Exact repaired helper blob: `r04_h3b_sheep_clip.py@100ddda513f433f33cd98704a0abab4d49e6c4da`, byte-equivalent to the strongest preserved helper successor for the combined source theorem. The prior focused suite `test_v4_h3b_sheep_clip.py@b13f221c16ad17442ededb226cc3363cb7d0e172` is retained unchanged. Additive current-ABI regressions live in `test_h3b_custody_closure.py@ce5464e631856a90665bc585c530cfd470fb2fd1` and cover missing configuration evidence, non-PASTURE SHEEP impostors, state/action preservation on rejection, and the canonical positive PASTURE/SHEEP path.

The H3b theorem remains narrow: an existing V233 sheep-worker HARVEST may be reprioritized within its assigned block only when next-refresh WOOL clipping is provable; service debt, cargo-return, malformed/nonstandard state, stale snapshots, final-day cases, and non-persistent multi-step reroutes fail closed.

## Authority boundary

This is still a default-OFF source repair. It does not add workers, animals, land, seed, market rows, service work, a new feature key, a sibling controller, a sibling V4 root, runtime/default activation, archive mutation, or Kaggle mutation. The stale PR's shared `apply_v4.py` and workflow remain deliberately excluded.

Source closure alone is not economics/promotion authority. Focused normal/optimized execution against the current canonical V233 seam plus repository control-plane/current-V233 gates remain required before merge; any future runtime wiring requires a separate current-native engagement/economics decision. Exact execution receipt and any central integration-ledger update must describe the bytes actually executed, not merely this source review.
