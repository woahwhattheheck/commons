# Titan measured-champion release admission

Operation: `titan-v3-measured-champion-firewall-20260909-sol`

Titan keeps exact release archives and now has multiple strong evaluation lanes,
but those are not the same thing as a release transaction. This package closes
the promotion boundary around
`runtime/integrated-selected/CURRENT-ARCHIVE.json`.

It does **not** alter gameplay, the active archive, configuration, or a provider.
It makes the next pointer change prove one of two things:

1. the selected bytes are an exact rollback to the preserved measured champion;
2. the selected bytes are a new measured champion whose paired-game evidence is
   complete, hash-bound, replayable with the trusted base-branch gate, and
   atomically committed beside a content-addressed historical archive.

The current pointer is intentionally grandfathered without calling it measured.
The champion ledger starts at the strongest preserved submitted baseline, Titan
V1 (`7b58fa06...0524`). This lets the project repair the release pointer without
inventing a V2.5 score and prevents an unmeasured integration package from being
promoted again.

## Admission states

- `BOOTSTRAP_MEASURED_BASELINE`: installs the immutable V1 ledger while leaving
  the active pointer byte-for-byte unchanged.
- `UNCHANGED_RELEASE`: normal development; pointer and champion ledger are
  unchanged. Policy may only be strengthened.
- `ROLLBACK_TO_MEASURED_CHAMPION`: the active archive becomes byte-identical to
  the ledger champion. No new strength claim is made.
- `PROMOTE_MEASURED_CHAMPION`: pointer, content-addressed history, source
  manifest, champion ledger, full evidence inputs, and a `PROMOTE` report all
  agree and the trusted base-branch paired-game gate reproduces the report.
- `BLOCK`: every other transition.

## Evidence directory

A new champion `SHA` must add exactly this addressable evidence packet under
`release_admission/evidence/SHA/`:

```text
CONTRACT.json
PROVENANCE.json
baseline.GAMES.jsonl
candidate.GAMES.jsonl
GATE.json
```

`GATE.json` uses the hardened `titan-v3-paired-game-gate` schema. Its four
input hashes and byte counts must equal the committed files, and its binding must
state that hashes cover the exact single-open private snapshots parsed by the
gate. The report must cover at least 16 unique seeds,
six unique opponents, both candidate seats, and 192 complete cells for both the
baseline and candidate. Every required robustness check must be present and
passing. The gate is then rerun from the **base checkout**, not from code changed
by the candidate PR, and the result must exactly equal the committed report.

The candidate `CURRENT-SOURCE.json` must also carry a `release_admission`
object binding the transition mode, candidate archive, previous pointer,
champion, and evidence directory. For a measured promotion its
`game_evidence_for_this_archive.new_full_games` value must cover the complete
candidate panel. This prevents a valid gate packet from being attached to stale
source metadata that still says the selected bytes have zero new games.

## Champion ledger transition

For a measured promotion, `CHAMPION.json` becomes:

```json
{
  "schema_version": 1,
  "champion_name": "human-readable-name",
  "archive_path": "exports/historical/titan-<SHA>.tar.gz",
  "archive_sha256": "<SHA>",
  "source_manifest_sha256": "<CURRENT-SOURCE SHA>",
  "previous_champion_sha256": "<OLD CHAMPION SHA>",
  "promotion_evidence_dir": "release_admission/evidence/<SHA>",
  "status": "measured_promotion"
}
```

The archive path is derived from its digest; aliases are rejected.

## Local verification

```bash
python3 -B -m unittest -v \
  revenue/kaggriculture/cloud-execution-lab/test_release_admission.py

python3 -B \
  revenue/kaggriculture/cloud-execution-lab/release_admission/guard.py \
  --base-root /path/to/base-checkout \
  --candidate-root /path/to/candidate-checkout
```

## Explicit non-claims

This guard does not increase gameplay strength, assert a current V2.5 score,
prove leaderboard generalization, or submit to Kaggle. Its job is narrower and
critical: preserve the strongest measured fallback and make future promotion a
reproducible evidence transaction rather than a pointer edit.
