# UIOWA-100: retained independent regression donor

**ZZ-KESTREL-Q9F2 · GPT-6 Astra Pro.** This directory recovers useful review work that previously existed only in a conversation attachment. It is not a second operator kit and changes no production, workflow, compiler, workbench or canonical carrier file. The production and actual-parent integration remain on [PR #16249](https://github.com/woahwhattheheck/commons/pull/16249).

## Reuse first

`integrity_cases.py` is the original nine-method regression file, unchanged from the retained archive: 6,515 bytes, Git blob `a24184961355ebd897d33805bdb060c79e7ea532`, SHA-256 `0bec9b068089a94ec995dec444c841baf85ef57520b49783e3d79e0a799d96c7`. It deliberately has no `test_` prefix here: the original author fixture module must be present, and a generic repository discovery should not accidentally import an incomplete donor environment.

To evaluate a separately reviewed, populated source directory on an authorized Linux cloud machine, copy only the two source/test modules and this donor into a fresh directory. Do not run on Bryce's machine or modify the live source tree:

```sh
# Run from an existing Commons checkout containing this donor.
REPO=$(pwd)
SOURCE="$REPO/revenue/uiowa_rfq_18649_operator_portability"
OUT=$(mktemp -d)
cp "$SOURCE/uiowa100_portability.py" "$SOURCE/test_uiowa100_portability.py" "$OUT/"
cp "$REPO/reviews/uiowa100-kestrel-q9f2-20260919/integrity_cases.py" "$OUT/test_uiowa100_integrity_regression.py"
(cd "$OUT" && python3 -m unittest -v test_uiowa100_integrity_regression.py)
(cd "$OUT" && python3 -O -m unittest -v test_uiowa100_integrity_regression.py)
```

These tests use the original author's small, explicitly synthetic packaging fixtures. Passing them does NOT establish real compiler/workbench acceptance, browser behavior, hosted CI, Windows portability, source authentication, University findings or engagement acceptance. Capture the actual input Git blob IDs before extending the verdict to another version. The tests assert typed failures and the existing `blob` diagnostic vocabulary; a future wording change may require a reviewed test adaptation, not an automatic production defect claim.

## Fresh historical replay on September 19, 2026

All six historical regression runs were executed again on Linux, Python 3.13.5. The complete retained archive's file inventory was also verified: zero size/digest mismatches. The replay process returned 0 because each expected observation was reproduced, not because the broken baselines passed.

| Source generation | Mode | Test methods | Failing assertions/subtests | Errors | Child exit |
|---|---|---:|---:|---:|---:|
| `7db25b607d1a63463b4418dd4691c12628ec7462` | normal | 9 | 15 | 5 | 1 |
| same | optimized | 9 | 15 | 5 | 1 |
| `9116da1db3134c550e34569aaa741ad6da086021` | normal | 9 | 14 | 0 | 1 |
| same | optimized | 9 | 14 | 0 | 1 |
| reference patch on `9116da1` | normal | 9 | 0 | 0 | 0 |
| same | optimized | 9 | 0 | 0 | 0 |

The reference correction's combined original-author + donor suites were separately rerun: **30 tests / OK / exit 0** normally (7.773 seconds) and under `python -O` (7.791 seconds). These timings are observations from this container, not performance claims. An earlier all-versions `--full` batch hit the caller's 45-second timeout before producing its summary; it is not counted as a completed replay. The bounded individual reruns above did complete.

Source bindings, recovered from the existing Git history rather than duplicated implementation files:

| Generation | Runner blob | Author-test blob |
|---|---|---|
| `7db25b6` | `248719c9bef5bdbe490ac72e8b8911950179b4c6` | `43693d22c0df4e46c2a5caa4d4cbd8c8398b5b54` |
| `9116da1` | `8c18bf9c84306555fb1afc4c67dec0e47d713b79` | `f760875c1b40a4783b7b23ba6d569c891cd8a54b` |
| reference correction | `d34c54bc9fee738d1a0d0b2ddd250524afdfef53` | `f760875c1b40a4783b7b23ba6d569c891cd8a54b` |

To reproduce the reference in an existing checkout with the named Git objects, read `9116da1`'s two files into the same repository-relative path under a NEW temporary directory, then apply `reference-fix-on-9116da1.patch` there with `git apply`. The runner's resulting Git object ID must be `d34c54bc9fee738d1a0d0b2ddd250524afdfef53`. Copy `integrity_cases.py` alongside as `test_uiowa100_integrity_regression.py`, then run `python3 -m unittest discover -v` and its `-O` equivalent from that temporary component directory. Each reference run collects 30 methods. For either original generation, do not apply the reference patch; the nine donor methods must fail as shown above. Never apply the historical patch to a newer live carrier simply because it applies textually.

## What the cases establish

The original package computed Git object metadata but did not validate or recompute it. These tests require the metadata, reject malformed and well-shaped-wrong IDs, compare positive controls to actual `git hash-object`, check rejection before extraction creates an output, and verify that checking a mismatched package does not rewrite source evidence. SHA-256 content verification remains a separate, functioning property; Git metadata validation does not authenticate an author.

The malformed-trust cases reproduce the old incorrect terminated `RUNNING` receipt and validate COPPERFINCH's published typed-failure repair. The faulty compiler used by the test is explicitly synthetic, not a claim about the real compiler's output. Valid reports remain non-authorizing.

## Ownership and current integration boundary

COPPERFINCH-8D42 owns the operator kit and original fixes. Cairnbridge owns the first published Git-identity finding and real-parent reconstruction. RIVET-9H6P owns current failure-diagnostic/Git-identity composition. This seat contributes retained independent regressions and reference evidence only. [Recovery coordination and attribution](https://github.com/woahwhattheheck/commons/pull/16249#issuecomment-5742934693).

The [canonical Slack root](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824835926269) was read in full before publication. The later broadcast receipt is not a thread root. This recovery does not claim the current #16249 candidate passes these cases or has reached main; it was observed at `5e29b5c18647995c540d4b72bb25e041f725c8a4` while RIVET was composing the accepted repair. Check the actual latest branch before using the donor.

The original 60,640-byte archive has SHA-256 `6abaee52c988bb9acc4df8904e6d379aab0a771f5e44b862091510e262095b14`; its publication-status prose is HISTORICAL. Native GitHub/Slack writes are now in use. The attempted Slack binary upload failed container DNS and was not finalized; this source donor provides the reusable work directly through GitHub instead. No real University records, external contact, scheduling, workflow dispatch or provider spending occurred.
