# H3b sheep max-held harvest-priority recovery

Canonical V4 source-custody recovery from PR #12603, exact source head `1deeee1c1509e6d767d485f139201ece5fb12af2`.

Preserved exact reviewed bytes only:
- helper `r04_h3b_sheep_clip.py`: Git blob `062d408cf84bc59b0f50dbfb31768684e3ef3828`;
- focused test `test_v4_h3b_sheep_clip.py`: Git blob `b13f221c16ad17442ededb226cc3363cb7d0e172`.

The stale PR's shared `apply_v4.py` and workflow are intentionally not carried. This recovery does not add or enable a feature key, change config/defaults, mutate the live router/runtime, execute a legacy materializer, or make an economics/promotion claim.

The preserved H3b theorem is narrow: an existing V233 sheep-worker HARVEST may be reprioritized within its assigned block only when next-refresh WOOL clipping is provable; service debt, cargo-return, malformed/nonstandard state, stale snapshots, final-day cases, and non-persistent multi-step reroutes fail closed. Any future wiring must be re-reviewed against the then-current canonical V233 state/accounting seam and remain default-OFF until separately promoted.
