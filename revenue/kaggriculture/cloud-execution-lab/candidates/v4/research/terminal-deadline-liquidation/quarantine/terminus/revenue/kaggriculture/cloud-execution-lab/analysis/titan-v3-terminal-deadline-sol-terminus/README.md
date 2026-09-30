# TITAN v3 terminal-deadline liquidation preservation

Operation: `titan-v3-terminal-deadline-liquidation-preservation-20260909-01`

## Defect

The canonical runtime creates a visible-state liquidation fallback at the final
executable step (`episodeSteps - 2`, normally step 718). Immediately after the
producer returns, however, both the inner runtime and outer entrypoint prefer the
raw producer selection. A deadline in the frozen SELL transform, history join,
or finalization can therefore return an action that never performed terminal
DROP/liquidation.

That is a deterministic cash-loss path, not a claim that it explains any entire
leaderboard gap. This packet measures and repairs only fallback precedence.

## Exact source custody

The derivation accepts only base commit
`15d39ea7a9048c880b5185ed9797cd4af717b27f` with these Git blobs:

- `main.py`: `4a8cf7bcda1f0fea231a144692cb84a779a9e73e`
- `titan_runtime.py`: `b952c9c228ecbde592bf3d2df01638677abb0d24`

`terminal_deadline_patch.py` renders both candidate files before writing either
one and rejects drift, symlinks, duplicate/missing replacement sites, and
reapplication. The hosted workflow applies it only in a detached disposable
worktree.

## Behavioral contract

- At the final executable step, visible-state terminal liquidation remains the
  fallback even after a producer has returned.
- On every nonterminal step, the prior completed-selection fallback behavior is
  preserved.
- Forced inner selected-transform expiry and outer finalization fallback both
  prove reachable cargo is dropped and all observed shed products are sold.

No canonical runtime/config/archive/pointer, provider state, Kaggle submission,
or promotion decision is mutated by this analysis packet. No score gain is
claimed without matched official-engine evidence.
