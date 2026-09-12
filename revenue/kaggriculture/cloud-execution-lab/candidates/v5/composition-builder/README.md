# Titan V5 pairwise composition builder

This directory exists to keep V5 convergence honest: one baseline archive, two exact component postimages, and the four comparable variants `control`, `A`, `B`, and `A+B`. It does **not** create another Titan root and it does not decide whether a component is good.

`compose.py` overlays only files already present in the baseline archive, verifies every source postimage by SHA-256, applies only declared `TITAN-CONFIG.json` activation values, and fails closed when two components want different bytes at the same archive path or disagree on a config value. The output `COMPOSITION.json` records the exact baseline, component source identities, changed archive members, activation values, and hashes of all four generated archives.

## Manifest

A manifest has exactly two components:

```json
{
  "schema": "titan-v5-composition-v1",
  "baseline": {
    "sha256": "<exact baseline archive sha256>",
    "member_count": 75
  },
  "components": {
    "joint_liquidity": {
      "files": [
        {
          "archive_path": "frozen_selected.py",
          "source_path": "frozen_selected.py",
          "sha256": "<exact source postimage sha256>"
        }
      ],
      "config": {
        "consumer": "frozen",
        "funding": true
      }
    },
    "productive_worker": {
      "files": [
        {
          "archive_path": "spatial_tempo.py",
          "source_path": "spatial_tempo.py",
          "sha256": "<exact source postimage sha256>"
        },
        {
          "archive_path": "worker_job_value.py",
          "source_path": "worker_job_value.py",
          "sha256": "<exact source postimage sha256>"
        }
      ],
      "config": {
        "consumer": "frozen"
      }
    }
  }
}
```

`source_path` is resolved under `--source-root`; the expected digest is mandatory so a moving checkout cannot silently change the experiment. Config entries are activation requirements: existing keys are set to those exact values in the applicable variant. Unknown keys are rejected rather than smuggled into the package.

## Build

```bash
python3 -B compose.py \
  --baseline /path/to/frozen-baseline.tar.gz \
  --source-root /path/to/commons/revenue/kaggriculture/cloud-execution-lab \
  --manifest pair.json \
  --output /tmp/titan-v5-pair
```

The output directory contains deterministic rebuilt archives plus `COMPOSITION.json`. Competitive evaluation should run the same opponent, seed, seat and engine identity for all four variants. A composition is promotion-worthy only when `A+B` improves the matched margin relative to **both** `A` and `B`; repository inclusion alone is not an activation or performance claim.

The builder intentionally refuses to combine different postimages of the same archive member. If two policies touch the same file, first converge them on canonical V5 `main`, then treat that converged postimage as one component instead of manufacturing an unreviewed textual merge in the experiment harness.
