# Frozen terminal decisions against recorded rivals

This is a separate downstream evaluation of PR10215's immutable decision file.
It does not call a selector, regenerate a scenario, infer history, invoke a
production actor, or run a new complete game. Rival private state and current
orders enter only this offline evaluator, after all decisions were fixed.

## Source and clock binding

The decision file SHA256 is
`bc5076379363ac998e2b7bb69cf3e1b936c6ddaca4711b95f66856014c36fa88`.
It is retained in Library `TITAN-JH-DELIVERY-PR10168-10175-10215.zip` as
`wool/evidence/WOOL-RESULTS.json`. Use that original file, not regenerated output.

Reuse the original `prism-late-milk-choice-evidence-20260907.zip`, SHA256
`2f8566ed9cd7cd04d342216c9eb5922f3d8bd361ffd952994439e10e9771907a`,
and LARCH's `TITAN-LARCH-public-history-inputs-20260908.zip`, SHA256
`b64a2363365b4e6711c08c38b3398bc44466994ef3d4d75da2a35be9d8488568`.
All 72 original archive members are checked, along with exact compressed and
decoded trace and public-input identities. Detailed archives stay private.

The raw recorder stores post-action rows. Input to decision718 is row718,
recorded as step717; the actual actions are in row719, recorded as718. Normalize
the public step to718 exactly as the original actor driver did. Reconstruct both
players' actual pre-unit private state from the recorded observations, preserving
shared public references, then execute the complete native final transition.
No inverse inventory reconstruction or hidden-stock assumption is required.

Before applying a frozen alternative, the original action must reproduce BOTH
the recorded terminal scores and every terminal observation field. All16 source
records passed this check. A mismatched baseline stops before an alternative.

## Result

The original16 source records remain12W/4L after the terminal substitution.
Fourteen complete actions differ, but no win/loss verdict changes. Six records
improve margin, eight are equal, and two worsen it. Ten unique own-input payloads
instead give four positive, four equal, and two negative cases; these still are
not independent samples. The source bank has two old development seeds and
multiple arms and seat mirrors.

The adverse pair is ONE original Arlene matchup mirrored. Own cash decreases40,
rival cash increases37, and margin worsens77. The original72082/70108 scores
become72042/70145, still a win. Its actual rival queue is outside the explicit
scenario family. Positive margin changes136 and8 are retained as well. The
complete per-record report is private; aggregate sums and separate multiplicity
accounting are in `WOOL-ACTUAL-SUMMARY.json`.

This is the important model boundary: nonnegative margin changes in every
included scenario did not prevent a negative change against an excluded actual
rival queue. The earlier conditional certificate remains valid for its table;
it was not a whole-game or out-of-family guarantee. No default, canonical agent,
release, hypothesis, or selected action was retuned after this finding.

## Execute

Reuse the existing POLY package's pinned engine and engine loader. The loader
runs in a separate Python process; all cache files must already exist, and engine
Python-source hashes are checked before import. No new export or download is
required.

```sh
python -B revenue/kaggriculture/cloud-market-response/evaluate_frozen_wool_outcomes.py \
  --choices "$DELIVERY/wool/evidence/WOOL-RESULTS.json" \
  --original-archive "$PRIVATE/prism-late-milk-choice-evidence-20260907.zip" \
  --input-archive "$PRIVATE/TITAN-LARCH-public-history-inputs-20260908.zip" \
  --engine-loader "$POLY/dependencies/engine_loader.py" \
  --engine-dir "$POLY/engine" \
  --output "$PRIVATE/frozen-wool-actual-outcomes.json"

python -B revenue/kaggriculture/cloud-market-response/test_frozen_wool_outcomes.py
```

Thirteen boundary methods pass without private inputs or an engine. They check
clock/action/input matching, unchanged workers, baseline score and full-state
failures, exact frozen-file binding, and preservation of differing actual-rival
consequences rather than hiding them in duplicate counts. The actual evaluator
executes30 terminal transitions:16 baselines and14 changed decisions. Zero
solver/selector, actor, full-game, or new-game-seed calls are made.

## Reporting-name and CI follow-through

PR10215's source/spec/manifest checks passed. Its original open-door run34189377877,
job101944107208, matched the legacy result-map name as a verb-list term near game
output fields. The report map is not an Action Pad interface. A descriptive
constant now names the SAME serialized key, with no format or behavior change.
Neither the guard nor its rules are modified.

Substituting that constant yields the exact original experiment abstract syntax
tree. Its eight boundary methods still pass. Current `WOOL-FREEZE.json` changes
only the script pin and adds this chronology; the original pre-execution manifest
remains at PR10215's merge95c5b22a. Its original immutable decision file remains
the sole input to this evaluator. The evaluator's analogous naming refactor was
also executed: every summary and per-record result is identical to its first
run, with both receipts retained. This repetition adds no independent evidence.

The final evaluator Git blob is `b7c1d16fff4c51ced47d133d78371dfed103e965`;
test blob is `98af8c61e5a13ffa60cbda5376e9ea33ba827c45`. Hosted checks for this
follow-through must be read separately; this local result does not imply they
have completed.
