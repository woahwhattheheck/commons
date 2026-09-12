# TITAN V5 exact-V3.1 champion floor

This is the control-plane/evidence half of `TITAN-V5-V31-CHAMPION-FLOOR-RELEASE-WIDE`.

## Why this exists

The V5 paired-economics release firewall correctly requires a candidate to be non-regressive against the **expected-old release pointer**. That closes V4→V5 regression, but it does not by itself enforce the owner acceptance target that repaired V5 also match or exceed exact submitted V3.1. If the expected-old pointer is V4, a candidate can beat V4 yet remain below V3.1.

This validator makes the immutable champion floor explicit:

- V3.1 source: `a90d888f03987ef0b35cfd20ec3519c6144db08a`
- V3.1 Kaggle submission: `56172377`
- V3.1 archive SHA-256: `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`

A report is admitted only when those exact authorities are present and a V5 candidate has nonnegative aggregate paired margin delta versus V3.1 on a canonical balanced panel: at least two explicit opponents, at least four identical seeds per opponent, and both seats for every opponent/seed.

## Intended convergence

This is **not** another evaluator, policy tree, release pointer, or gameplay implementation. The producer should reuse the existing authenticated `archive-version-bridge` / `joint-liquidity-bench` execution closure and emit raw per-cell scores for exact V3.1 and the exact V5 candidate.

After the paired-economics firewall (#13409 successor lineage) is canonical, the same V5 release transaction should require **both**:

1. expected-old release → candidate paired-economics PASS; and
2. exact V3.1 champion → same candidate champion-floor PASS.

The two admissions must bind the same candidate ID/archive, engine/opponent authority, and the same opponent/seed/seat topology. `topology_sha256`, `opponent_ids`, and `seed_ids` are emitted specifically so the follow-on release replay can fail closed on panel substitution.

No default/config/runtime/archive/Kaggle mutation belongs in this directory.

## Focused gate

```bash
python -B -m py_compile champion_floor.py test_champion_floor.py
python -B -m unittest -v test_champion_floor.py
python -O -B -m unittest -v test_champion_floor.py
```
