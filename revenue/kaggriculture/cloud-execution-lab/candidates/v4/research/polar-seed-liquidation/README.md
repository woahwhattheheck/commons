# POLAR seed liquidation economics

Claim `POLAR-20260911-SEED-SHADOW`. Research-only calculator for the ONE V4 queue.

Pins:
- interpreter `465f4263da1c98acf78889d67cdd21b61dbba145`
- engine blob `3c202c7ee921da239356789e266b694635103fc4`

The calculator values extra yield by walking the isolated same-item book one unit at a time after already-committed output. It does not use `current_quote * extra_yield`. Owned seed is a sunk cost and is not charged as a purchase. Results here do not authorize skipping authored PLANT or BUY_SEED.

Run:

```
python3 -m unittest test_polar_seed_liquidation.py
python3 polar_seed_liquidation.py
```
