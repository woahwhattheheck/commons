# TITAN V5 V3.1 champion ratchet

`champion_gate.py` is an evidence-only objective floor for the single V5 line.
It exists because incremental release no-regression against the current pointer
is insufficient when the starting V4/V5 lineage is still below the exact
submitted V3.1 champion.

The gate accepts one balanced raw panel containing incumbent, exact V3.1, and
candidate scores on identical `(opponent_id, seed, seat)` cells. It binds the
submitted V3.1 archive SHA-256 directly and recomputes all comparisons.

A PASS requires:

- at least two opponents, at least four identical seeds per opponent, both seats;
- exact submitted V3.1 archive `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`;
- candidate total own score non-regressive vs the incumbent;
- candidate total own score **strictly above** V3.1;
- candidate paired margin non-regressive vs both incumbent and V3.1;
- no incumbent/champion win-or-tie becoming a candidate loss; and
- nonnegative candidate own-score deltas versus both baselines in every
  opponent × seat stratum.

This does not mutate runtime, defaults, archives, pointers, or Kaggle. It is
intended to be consumed by the current V5 release boundary after the paired
competitive-economics firewall lands.
