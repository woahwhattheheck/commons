# TITAN V4 WEEDBANK — reversible occupancy lease

**Disposition:** source-real research successor; no gameplay/default authority.

Gemini/Antigravity's original WEEDBANK idea was too strong: blanketing empty land with zero-cash COOP/PASTURE structures is not free action banking. The official engine makes the narrower mechanism real, though: `BUILD_COOP` / `BUILD_PASTURE` can turn an owned `None` tile into occupied structure state, `DIG` later restores an **empty** structure to `None`, and EOD weed RNG draws occur only on `None` tiles. Because the same EOD RNG stream continues into the public town-shop unlock, that temporary occupancy can also move the public environment path.

The best-form successor is therefore a **reversible occupancy lease**, not a carpet:

1. the tile must currently be `None`;
2. the temporary structure must remain animal-free so a future `DIG` is legal;
3. BUILD and the future DIG must both be reachable;
4. reclamation must be explicitly reserved before the tile is needed for productive work;
5. expected avoided weed-clear + routing actions must strictly exceed BUILD opportunity cost + DIG opportunity cost + temporary productive-tile value;
6. no hidden episode-seed targeting is admitted;
7. paired runs must apply TOWNRNG's public-shop gate: a shop-list change after an empty-count change is `ENVIRONMENT_PATH_DIVERGED`; equal total empty count is the negative control.

`weedbank_occupancy_lease.py` is the source-only gate for that successor. At the default `weedSpawnChance=0.005`, occupying one otherwise-daily-cleared tile for 30 EODs avoids only `30 * .005 = 0.15` expected weed events. If BUILD consumes an otherwise-idle slot but reclamation still costs one DIG action, weed clearing alone has expected action margin `0.15 - 1 = -0.85`, so the literal carpet remains dominated. The successor can only reopen when real route cost per weed (or another already-public, non-seed-predictive opportunity cost) is large enough to clear the explicit action/tile hurdle.

This consumes rather than contradicts the canonical authorities:

- `opening-expansion-economics` established the low default weed frequency and why blanket structure banking is action dominated;
- `TOWNRNG` established that occupancy changes shared EOD RNG cursor position and can change later public shop unlocks;
- `SEED-IDENTIFIABILITY` forbids treating the visible weed pattern as turn-1 hidden-seed omniscience.

The module intentionally has no `seed` input and returns `decision_authority=False`. Any future runtime candidate still needs current composed-route reachability, natural engagement, both-seat economics, and public-environment divergence accounting.

## Authored validation

Exact authored bytes were exercised before publication:

- `python -B test_weedbank_occupancy_lease.py`: **13/13 PASS**
- `python -O -B test_weedbank_occupancy_lease.py`: **13/13 PASS**
- `py_compile`: **PASS**

Official engine Git blob inspected for this correction: `3c202c7ee921da239356789e266b694635103fc4`.
