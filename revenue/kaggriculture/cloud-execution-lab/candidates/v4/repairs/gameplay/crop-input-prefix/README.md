# Native crop input restoration: executable-prefix repair

One component of `main:revenue/kaggriculture/cloud-execution-lab/candidates/v4`,
not a successor V4 or another crop controller. Owner: ASTRA-ROOTSTOCK.

## What was broken

`crop_release.propose_input_repair` already restricted sales, future funding,
and price bounds to the first ten raw market rows. Two earlier screens instead
read the entire queue: the existing-WHEAT-buy conflict and physical-purchase
capacity bound. The official interpreter ignores rows at indices 10 and later.
A dead WHEAT purchase therefore vetoed real input restoration, a dead large
FERTILIZER/animal purchase invented a capacity obligation, and an invalid dead
purchase could produce a rejection or exception.

The repair changes those two scans to `orders[:10]`. It does **not** compact,
truncate, reorder, or sanitize the returned queue. All empty positions, live
purchases, inherited rows and dead suffix bytes remain present. Existing exact
returned-action and subsequent observed-fill bindings still control debt credit.
This preserves the crop mechanism's existing standard-configuration contract;
it does not add support for different market caps or create an available slot.

## Source custody and composition

The native input is `crop_release.py` blob
`dd318e5bbe6245913c3dcb8c07d0752fd1ebd735`, recovered from existing workflow
artifact `10175943272`, `final-pressure-runtime/`, and matched to live main.
`compose_crop_input_prefix.py` authenticates the exact top-level method, makes
the two replacements, and preserves every unrelated source byte. Applying the
same repair twice is exact identity. Unknown/partial/decorated/duplicate method
versions are rejected, not silently replaced. The CLI refuses overwriting a
source, existing destination, or symlink. On this input the component output is
`ddcb07738d34c0327842ebd3ca3efbd1177ab6fe` (SHA256 in `RECEIPT.json`).

The native V4 composer can consume this one recipe in its scratch component.
Same-method peer changes need explicit composition and retesting. Do not run a
legacy R04 materializer, introduce another crop key, or copy a whole old runtime
over current peers. No production module, feature default, archive, workflow,
or Kaggle submission is changed by this package.

## Execute

`RUNTIME` must be an authenticated extracted native package containing the nine
source pins checked by the suite, including the existing official engine/loader.
The checks compose in memory; the source runtime is not overwritten.

```sh
python check_crop_input_prefix.py --runtime "$RUNTIME" --output /tmp/crop-prefix-normal.json
python -O check_crop_input_prefix.py --runtime "$RUNTIME" --output /tmp/crop-prefix-optimized.json
python run_crop_prefix_controls.py --runtime "$RUNTIME" --output /tmp/crop-prefix-controls.json
python -O run_crop_prefix_controls.py --runtime "$RUNTIME" --output /tmp/crop-prefix-controls-O.json
python compose_crop_input_prefix.py "$RUNTIME/crop_release.py" /tmp/crop-prefix-component.py
```

For the inherited suite, construct a separate scratch copy of the native package
with only `crop_release.py` replaced by the composed bytes. From that scratch
root run `PYTHONPATH=. python checks/test_crop_release.py` and its `python -O`
equivalent. The original test file is unchanged, blob `19720197551d83cd22f9223c614d4c2efc4c8ecb`.

## Executed result and limits

New checks: **16/16 normal and 16/16 optimized**. Per mode: 151 full official
interpreter calls, 72 exact observed-fill/debt receipts, 60 dead-suffix vectors,
56 live-prefix controls and eight actual SpatialTempo crop lifecycle calls.
Inherited crop checks: **22/22 normal and 22/22 optimized**. Eight broken variants
are assertion-killed in each mode; infrastructure/error-only failures do not
qualify. Detailed identities, rejection counts and execution hashes are in
`RECEIPT.json`; every substantive assertion remains active under `-O`.

The constructed step-457 witness retains the three owed WHEAT in both seats,
while immediate own cash is $72 lower because those units were not sold. This
is operating-input restoration evidence, **not a positive cash-margin claim**.
No full game, natural engagement census, whole-assembled-V4 deadline panel,
hosted comparison, or competitive expected-value gate was performed here.

Claim and execution handoff:
https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789181145018989
