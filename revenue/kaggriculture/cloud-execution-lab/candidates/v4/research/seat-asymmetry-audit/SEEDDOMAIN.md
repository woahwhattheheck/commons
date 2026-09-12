# TITAN V4 SEEDDOMAIN — episode-seed provenance and finite-panel consensus

**Disposition: research-only source/provenance closure inside the existing `research/seat-asymmetry-audit/` authority. No runtime/controller/default/config/COMPOSITION/INTEGRATION/archive/Kaggle mutation.**

SEEDDOMAIN is the source-bound successor to merged SEEDSTREAM #13090. It answers the prerequisite left open by #12898 and #13090: *what seed domain, if any, is actually complete enough to enumerate?*

## Pinned source theorem

The pinned Kaggle seed utility (`utils.py` Git blob `91c8822ee6201ba4a5a8416c7dbe34f95dd61c87`) resolves an episode seed in this order:

1. preserved `env.info["seed"]`;
2. explicit `configuration.seed`;
3. caller fallback, otherwise `random.randrange(2**31)`.

It then clears the seed from configuration and persists the resolved value in `env.info`.

The pinned Kaggriculture config (`kaggriculture.json` blob `b354d06b742fe48402513792253f1a5c29366b20`) declares `seed` only as `integer | null`, default `null`; it contains **no `minimum` or `maximum`**. Therefore the pinned engine schema itself supplies no finite complete domain for an explicitly provided seed (nor for a seed already preserved in `env.info`).

The fallback path is different: when it is genuinely taken and no custom fallback is supplied, source gives the complete finite interval:

```text
0 <= seed < 2**31
```

That is 2,147,483,648 candidates. Its finiteness is a provenance fact, **not** authorization to brute-force it in production.

The pinned offline evaluator (`evaluate.py` blob `1fb6b655bb4ca1e1684be165a8ef513e2e6c2325`) explicitly executes:

```text
cfg.seed = seed
engine.interpreter(...)
assert cfg.seed was scrubbed
```

so an offline experiment may legitimately define a smaller finite candidate domain when it first byte-binds the exact precommitted seed panel. The candidate agent still never receives the seed itself.

## Why this changes SEEDSTREAM's boundary

Merged SEEDSTREAM correctly says a singleton from an arbitrary bounded search is only `BOUNDED_UNIQUE_NOT_GLOBAL`. SEEDDOMAIN makes the provenance classes explicit:

| provenance | complete finite domain from pinned source? | permitted conclusion |
|---|---|---|
| implicit default fallback | yes: `[0, 2**31)` | source-complete fallback interval only |
| explicit `configuration.seed` | **no** | external provenance required |
| preserved `env.info.seed` | **no** | external provenance required |
| byte-bound offline panel manifest | yes, for that experiment only | exact finite panel set only |

Nothing here proves which provenance path a hosted Kaggle episode uses. Hosted/global seed authority remains false unless that runner provenance is independently authenticated.

## Authenticated finite-panel set

`seed_domain_provenance.py` defines a minimal byte-bound research receipt:

```json
{
  "schema": "titan.v4.authenticated-offline-seed-panel/v1",
  "seeds": [1, 7, 255],
  "evaluator_git_blob": "1fb6b655bb4ca1e1684be165a8ef513e2e6c2325",
  "engine_git_blob": "3c202c7ee921da239356789e266b694635103fc4",
  "seedstream_git_blob": "c02ab05ed7684508f02e383fa3281f29e2f60fa6"
}
```

The complete manifest bytes are SHA-256 bound before use. Duplicate JSON keys, wrong source blobs, empty/duplicate seeds, bool/float/string seed poison, extra fields, or byte drift fail closed.

A bound panel is labeled only `AUTHENTICATED_OFFLINE_PANEL_SET_ONLY`.

## Public-evidence filtering and consensus

SEEDDOMAIN does **not** reimplement the RNG. It authenticates and loads merged `seed_stream_identifiability.py@c02ab05...`, then applies the same public-only EOD evidence to just the declared finite seed set.

Possible results are:

- `NO_MATCH_IN_AUTHENTICATED_PANEL_SET`
- `AMBIGUOUS_IN_AUTHENTICATED_PANEL_SET`
- `PANEL_SET_UNIQUE_NOT_GLOBAL`

Even the last verdict keeps all of these false:

```text
hosted_seed_domain_proved = false
global_identifiability_proved = false
production_seed_cracker_authorized = false
```

Future predictions are delegated to SEEDSTREAM's all-survivor consensus primitive. No first-candidate, MAP, or guessed-seed shortcut is introduced.

## Intended use

This closes two opposite failure modes at once:

1. **false omniscience** — treating a convenient `[0,N)` developer search as the hidden game's complete seed domain;
2. **throwing away legitimate finite experimental knowledge** — an offline paired panel already precommits a finite exact seed set, so public observations may be used to partition that set for research without reading the hidden seed.

A later RNG-sensitive gameplay experiment may consume this only as offline evidence. Turning it into a live policy would require a separate theorem that the live environment exposes an authenticated complete domain and that no test-bank overfit is introduced.

## Validation

Authored-byte gate before publication:

```text
PASS 13/13 seed-domain-provenance tests
PASS 13/13 under python -O
py_compile PASS
```

The checkout-aware source-auth test runs automatically when the canonical repository layout is mounted. A repo-mounted exact-head source-auth + CLI receipt remains the publication gate because this cloud seat does not carry the repository checkout.
