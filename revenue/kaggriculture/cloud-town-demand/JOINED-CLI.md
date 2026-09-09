# Captured-reader adoption and complete CLI disposition

`joined_case.py` now explicitly adopts FLOW's landed saved-input reader `f5f64be61dd6277e8436d930286498486ff4f2de`. The reader's source file is compiled from the same captured bytes whose identity is checked. Normal module metadata is retained; a failed or cancelled reader body restores only this loader's prior alias. Transitive import side effects are not rolled back. This is direct consumption of FLOW's repair, not another dependency loader.

The CLI retains its original default of 200,000 market units and no time cutoff. Optional `--max-units` and `--seconds` forward directly to the existing reader/FLOW budget. No pricing, ranking, scenario, controller or producer logic changes.

A complete result prints its conditional choice and exits0. An incomplete or invalid FLOW result writes its full existing report, prints the unchanged reason and a null choice, and exits3. Input/source/file errors exit2 with a concise diagnostic. Existing output files are never overwritten; use a new output path. Parent output directories are created as needed. Cancellation is not swallowed.

## Actual reproduction and limits

Fifteen focused methods pass. The exact original CLI fails thirteen methods: several exercise newly introduced options/helper behavior rather than thirteen separate bugs. The original also fails the independent default-options duplicate-scenario fixture with `TypeError` while dereferencing its absent ranking; the revised command retains `invalid_flow` and exits3. Its ordinary fresh run loads the newly adopted reader successfully and reproduces the entire retained nine-scenario report except reader provenance and elapsed time: eighteen route/scenario records and3,915 signed cash rows are unchanged. Zero-clock and one-unit-budget cases retain no ranking or partial scenario rows. Source metadata, captured execution, cancellation restoration, output preservation and input mutation boundaries are covered.

No actor, engine transition, physical tail, game, seed or selected-policy change is included. Original PR10239/PR10268 source evidence remains immutable. The cooperative FLOW budget is not a hard process timeout.

## Source closure

Pass the exact declared source closure, not an arbitrary moving-main checkout. The adopted reader explicitly pins FLOWddbbe439 and DATE5e418aec. PRISM's later objective source is a separate input requiring the reader owner's explicit pin adoption; this delivery does not silently replace it. Prior tested reader revisions remain accepted for reproducing historical results.

```sh
python -B joined_case.py --input saved-226-row.json --paths declared-paths.json \
  --source-root "$PINNED_SOURCE_ROOT" --engine "$ENGINE/kaggriculture.py" \
  --output /tmp/new-town-flow.json --seconds 0
# A budget-limited result is preserved; process exit is 3, not a traceback.
```

The regression command reuses the saved exact input, original complete result, old source closure and current captured-reader closure:

```sh
python -B test_joined_cli.py --source-root "$CAPTURED_SOURCE_ROOT" \
  --prior-root "$PRIOR_SOURCE_ROOT" --input saved-226-row.json \
  --paths declared-paths.json --reference joined-result.json \
  --engine "$ENGINE/kaggriculture.py" --report /tmp/cli-result.json
```

Full logs, exact old/new source, reference report and the changed reader are preserved in the companion Library delivery; the existing PR10239 archive supplies the shared original input/engine/dependency closure. No full enumeration or earlier game panel is repeated.

Owning-thread claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788845832036599
