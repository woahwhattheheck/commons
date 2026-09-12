# TITAN V5 single staging composer

This is the convergence surface for **one** production-v3/V5 candidate. It is not a new policy, selector, evaluator, or release path. Gameplay owners keep their own source, tests, and economics; a component becomes composable only after that lane can hand off exact replacement/addition bytes plus a manifest bound to the current production-v3 archive.

The baseline is fixed to production-v3 SHA256 `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`. The composer single-captures and authenticates that archive, applies component manifests in the explicit CLI order, and emits one deterministic archive plus one receipt. Untouched members remain byte-identical.

## Component handoff

Each component directory contains `COMPONENT.json` and its source files. The manifest schema is `titan-v5-staging-component/v1`. Existing replacement-only manifests remain valid; `additions` is optional and is used only for members that are absent from the current composed archive at that component boundary:

```json
{
  "schema": "titan-v5-staging-component/v1",
  "component_id": "p01-productive-expansion",
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
  "additions": {
    "p01_productive_expansion_gate.py": {
      "source": "p01_productive_expansion_gate.py",
      "postimage_sha256": "<exact new member SHA256>"
    }
  },
  "kaggle_submission_hold": true
}
```

A replacement must target a member already present in the current composed archive and bind its exact current preimage. An addition is the inverse: its member must be absent at that exact boundary, and its source bytes must match the declared postimage. Two components cannot add the same member. If a later reviewed component replaces a member that an earlier component added, the normal overlap rule applies: the later component must name the immediately preceding writer in `overlap_after`, and its preimage must match that writer's exact postimage.

A later component may touch any member already replaced in the same composition **only** when it names the immediately preceding writer in `overlap_after` and its preimage hash matches that writer's exact postimage. This deliberately refuses implicit textual merges: colliding gameplay owners must first produce one reviewed combined postimage.

`depends_on` components must already appear earlier in the composition order. `conflicts_with` is enforced in either direction. Component IDs are unique. Manifest JSON is strict (duplicate keys and non-finite values reject), member/source paths are canonical relative paths, symlinked component sources reject, and every source body must match its declared postimage.

## Build

```bash
python -B staging_composer.py \
  --baseline /path/to/production-v3.tar.gz \
  --component /path/to/p01/COMPONENT.json \
  --component /path/to/p05/COMPONENT.json \
  --out /fresh/v5-staged.tar.gz \
  --receipt /fresh/v5-staged.json
```

The receipt binds baseline/candidate SHA256, every component-manifest SHA256, ordered dependencies/conflicts, replacements with exact pre/post identities, additions with explicit absence preconditions and postimages, complete final member hashes, and `kaggle_submission_hold=true`.

Publication delegates to the sibling `publication_custody.publish_exclusive` helper rather than maintaining a private transaction implementation. Output paths are create-only: both finals are reserved before either payload is written, reservation descriptors stay open through payload writes/fsyncs and rollback ownership checks, and each final pathname is re-opened and re-authenticated as a regular file with the exact reserved device/inode and exact payload before parent directories are fsynced. Failure cleanup removes only pathnames that still resolve to an inode owned by this invocation, so a foreign replacement is preserved. The shared helper is the canonical publication-custody contract. This is a fail-closed verification boundary; it does not claim that an untrusted actor can never rename a pathname after the final check.

## Boundary

This tool answers only: **can these exact reviewed component bytes be composed without silently changing any other production-v3 member?** It does not decide whether a component won a screen, whether interactions are economically positive, or whether the resulting archive is eligible for CURRENT/release/Kaggle. Those gates remain separate. Do not use the composer to smuggle unmeasured fixes into V5.

Focused gate:

```bash
python -B -m py_compile staging_composer.py test_staging_composer.py test_staging_composer_additions.py test_staging_composer_publication.py publication_custody.py test_publication_custody.py
python -B -m unittest -v test_staging_composer.py test_staging_composer_additions.py test_staging_composer_publication.py test_publication_custody.py
python -O -B -m unittest -v test_staging_composer.py test_staging_composer_additions.py test_staging_composer_publication.py test_publication_custody.py
```
