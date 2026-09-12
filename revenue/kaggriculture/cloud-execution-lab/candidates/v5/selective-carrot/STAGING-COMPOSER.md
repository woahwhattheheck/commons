# TITAN V5 single staging composer

This is the convergence surface for **one** production-v3/V5 candidate. It is not a new policy, selector, evaluator, or release path. Gameplay owners keep their own source, tests, and economics; a component becomes composable only after that lane can hand off exact replacement bytes plus a manifest bound to the current production-v3 archive.

The baseline is fixed to production-v3 SHA256 `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`. The composer single-captures and authenticates that archive, applies component manifests in the explicit CLI order, and emits one deterministic archive plus one receipt. Untouched members remain byte-identical.

## Component handoff

Each component directory contains `COMPONENT.json` and its replacement source files. The manifest schema is `titan-v5-staging-component/v1`:

```json
{
  "schema": "titan-v5-staging-component/v1",
  "component_id": "p05-weed-rejoin",
  "baseline_archive_sha256": "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239",
  "depends_on": [],
  "conflicts_with": [],
  "overlap_after": {},
  "replacements": {
    "r04_full_router.py": {
      "source": "r04_full_router.py",
      "preimage_sha256": "<exact current member SHA256>",
      "postimage_sha256": "<exact replacement SHA256>"
    }
  },
  "kaggle_submission_hold": true
}
```

A later component may touch a member already replaced in the same composition **only** when it names the immediately preceding writer in `overlap_after` and its preimage hash matches that writer's exact postimage. This deliberately refuses implicit textual merges: colliding gameplay owners must first produce one reviewed combined postimage.

`depends_on` components must already appear earlier in the composition order. `conflicts_with` is enforced in either direction. Component IDs are unique. Manifest JSON is strict (duplicate keys and non-finite values reject), member/source paths are canonical relative paths, symlinked replacement sources reject, and every source body must match its declared postimage.

## Build

```bash
python -B staging_composer.py \
  --baseline /path/to/production-v3.tar.gz \
  --component /path/to/p05/COMPONENT.json \
  --component /path/to/p02/COMPONENT.json \
  --out /fresh/v5-staged.tar.gz \
  --receipt /fresh/v5-staged.json
```

The receipt binds baseline/candidate SHA256, every component-manifest SHA256, ordered dependencies/conflicts, per-member pre/post identities, complete final member hashes, and `kaggle_submission_hold=true`. Output paths are create-only; both finals are reserved before either payload is written and owned reservations are rolled back on ordinary write/publication failure.

## Boundary

This tool answers only: **can these exact reviewed component bytes be composed without silently changing any other production-v3 member?** It does not decide whether a component won a screen, whether interactions are economically positive, or whether the resulting archive is eligible for CURRENT/release/Kaggle. Those gates remain separate. Do not use the composer to smuggle unmeasured fixes into V5.

Focused gate:

```bash
python -B -m py_compile staging_composer.py test_staging_composer.py
python -B -m unittest -v test_staging_composer.py
python -O -B -m unittest -v test_staging_composer.py
```
