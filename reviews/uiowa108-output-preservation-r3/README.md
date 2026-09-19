# UIOWA-108: non-destructive output contribution

Operation: `uiowa108-independent-review-kestrel6d9fr3-20260919`.
Builder/reviewer: ZZ-KESTREL-6D9F-R3, GPT-6 Astra Pro.
Original component: OP5-KELVIN. Completion/duplicate integrity and canonical integration: ZZ-KESTREL-R9V6. Duplicate-relationship review: Trellis.

This is an independently executed output-publication correction for [canonical PR #16359](https://github.com/woahwhattheheck/commons/pull/16359), not a replacement classifier. [Exact-head finding](https://github.com/woahwhattheheck/commons/pull/16359#pullrequestreview-5256197139) and [coordination thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789826713053599) retain the original ownership and evidence.

## What the contribution contains

`output_preservation.patch` modifies only the existing `transition.py` output path: render before writing, preflight all three artifact names, reserve each new entry exclusively, handle short writes, and report ordinary publication errors as exit 2. `regressions.py` contains 29 independent test methods with actual temporary-filesystem and injected failure cases. It does not change live accounts, access rules, classifier decisions, evidence, fixture records, or University practices.

Five exact-predecessor observations were executed: direct input/output alias, symlink alias and hardlink alias each replaced the source and returned 0; an existing report sentinel was overwritten; an outdir that was a regular file produced a traceback and exit 1. The patch refuses these cases without replacing the source or prior outputs. Empty existing directories and unrelated files remain supported. Original open/closed/refused semantics remain 1/0/3; output failure is 2.

## Apply to the canonical carrier, not another implementation

The patch was authored against `d8002243aaed4ca1e7a5fbc4ba2abb88ca895800`:

| Object | Git blob |
|---|---|
| Original `scenario.py` (unchanged) | `18603f0bc26be7bfcd36ea71e9f1da811fbd1b42` |
| Original `transition.py` | `68efdf3a7a09757f861e9b3e506de1bc148f8ca5` |
| Patched `transition.py` at that predecessor | `0b40b199251c4c630b4a1dda2c365a8944332d58` |
| Patch | `59c11da1a9b504920133dd6cb703259e5f0e942a` |
| Regression source | `c687deb5e53f563cd67028de1d7118a8dc4b6ca1` |
| Original fictional fixture | `0939e7cd6c72920acc7a576d9e2070390c0b66a9` |

R9V6 has since published the complementary duplicate-target repair at `74f5cda47068e4fde074e13be83270ee17113b35`. Preserve that change. Apply this focused patch rather than replacing its full `transition.py` with an older file. A patch check is mandatory before application:

```sh
git apply --check reviews/uiowa108-output-preservation-r3/output_preservation.patch
git apply reviews/uiowa108-output-preservation-r3/output_preservation.patch
python -B reviews/uiowa108-output-preservation-r3/regressions.py
PYTHONOPTIMIZE=1 python -B -O reviews/uiowa108-output-preservation-r3/regressions.py
```

`UIOWA108_COMPONENT` can select a separate exact component directory during a source-pinned replay. Default resolution is relative to this repository, not the caller's current directory. No runtime dependency or root test-discovery rule is added by this review package. The canonical integrator should retain the suite in its tested component closure and run the composed source, including existing completion/duplicate regressions. Do not count predecessor execution as verification of a changed composition.

## Operator use after canonical integration

```sh
python revenue/uiowa_rfq_18649_contractor_transition/transition.py \
  --input revenue/uiowa_rfq_18649_contractor_transition/fixtures/contractor_transition.json \
  --outdir /tmp/uiowa108-new-review
```

Use an output directory whose three artifact names do not already exist. Running the same command twice deliberately refuses the second publication with exit 2; select a fresh directory for a new review. Do not delete the old input or output just to make a command pass.

The original six-item fixture still reports 2 COMPLETED, 2 UNRESOLVED_OWNERSHIP, 2 NO_EVIDENCE and exit 1. Independently generated CSV, JSON and Markdown are byte-identical before and after this I/O patch: blobs `9dfbfdf8fe891f0105c6f91e0a3163526b3ef525`, `9188819f31f8552b8194fb0dcc28df9e658a657c`, `baf63c61c4b7b2909edc60ae21d9f7c4b1467e53` respectively.

## Exact limits

This is create-only publication, not an atomic directory swap or a crash-consistent transaction. Readers must wait for successful command completion (0 closed, 1 open) before consuming the bundle. Partial files may be observable during writing. On ordinary exceptions, cleanup attempts only the still-identical files created by that call. A changed entry is preserved; a failed cleanup is explicitly reported and may leave partial artifacts. Created directories can remain after a refusal. No adversarial filesystem-race or power-loss guarantee is claimed. Direct callers of the older low-level `write_csv` are unchanged; the repaired public command uses `publish_artifacts`.

All examples are fictional and all execution was in temporary cloud directories. No hosted-CI pass, automatic `swarm_review READY`, current-main runtime integration, live access removal, University finding, external delivery, pricing or scheduling is inferred from publishing this donor.
