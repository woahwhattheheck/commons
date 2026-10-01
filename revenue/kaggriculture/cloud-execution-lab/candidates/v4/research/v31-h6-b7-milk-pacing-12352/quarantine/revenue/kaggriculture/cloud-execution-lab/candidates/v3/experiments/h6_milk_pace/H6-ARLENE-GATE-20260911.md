# H6 MILK pacing — Arlene competitive gate

This receipt closes the current H6/B7 pacing experiment on competitive economics rather than own-value movement.

The candidate is the exact post-transform H6 R04 router (`sha256 9b84d5b9e2c6012c9d97d6aacce056bf1e8d01508bfeecec8811870b2db25f8a`) produced by the PR #12352 transformer. The mechanism caps requested MILK sales at 9 units/day on days 10–19, earliest-first and slot-stable, while repairing R04 sale debt so deferred units remain available later.

## Equivalence checks

- H6 OFF direct router reproduced exact V3.1 `main.py` terminal scores on seed 2027 versus Arlene in both seats.
- H6 ON direct router reproduced the full H6-transformed Titan runtime entrypoint on seed 2027 versus Arlene in both seats.

Those checks bind the measured direct-router semantics to the transformed runtime path before judging economics.

## Frozen Arlene result

Seeds `2611151001..2611151008`, both seats, 16 paired cells under the retained process-isolated official interpreter:

- completed: **16/16**; failures: **0**
- mean Δown: **+206.125**
- mean Δrival: **+924.625**
- mean competitive ΔM = Δown − Δrival: **−718.5**
- median ΔM: **−600**
- positive / tie / negative cells: **2 / 0 / 14**
- range: **−2181 .. +69**

The own-value number is misleading here: H6 improves the tested player's value on average, but improves the rival by roughly 4.5× as much. This is exactly the failure mode the competitive-margin gate was intended to catch.

## Disposition

**REJECT the current H6/B7 9u/day pacing policy.** Do not enable it, merge it into the submitted package, or spend additional promotion effort on this exact mechanism. The source carrier can remain as a negative experiment record, but it should not stay in the active promotion queue.

Any successor holding policy must explain and prevent the rival-price/supply benefit observed here, then re-enter through the same paired ΔM gate. Own revenue alone is not an acceptance criterion.

Exact per-cell deltas and custody hashes are in `H6-ARLENE-GATE-20260911.json`.
