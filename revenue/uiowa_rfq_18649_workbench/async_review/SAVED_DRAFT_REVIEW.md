# Saved-review text preservation: executable repair and independent browser evidence

**Seat:** ZZ-KESTREL-ASYNC14-U8 / GPT-6 Astra Pro. **Operation:** `uiowa-saved-draft-utf8-async14u8-20260919`, complementary to the retained ASYNC14 inspection review in this directory. All example notes, reports and byte failures are fictional test inputs, not University evidence.

## What the operator gains

A damaged saved-review file must not silently replace an analyst's existing notes with altered text. The repair reads the original file bytes and rejects invalid UTF-8 before replacing any of the twelve notes/dispositions. A valid literal replacement character, CJK, accents, emoji, multiline notes and empty notes remain legal. The current receipt, report, selection, filters, notes and dispositions survive a rejected restoration.

This is a **saved-draft** repair. RAW17's candidate/authority request transport and KESTREL-47's server numeric/Unicode decoder are separate work and remain unchanged. Keystone/Trellis retain production UI composition. BASALT-42 independently reproduced this defect and supplies complementary export/download tests. Do not install a second restore implementation or replace the newer presentation/keyboard app wholesale with a historical snapshot.

## Actual execution in this continuation

| Execution | Source | Result |
|---|---|---:|
| Reproduction at 15:02:57 UTC | composed c4c305db / app 808a8940 | 30/37; seven invalid encodings silently alter notes |
| Repair at 15:06:41 UTC | generated reference app e570dcac | 37/37 |
| Repair under real python -O, 15:06:54 UTC | same reference app | 37/37 |
| Published reusable runner, 15:10:57 UTC | runner 3c51ec05; same app | 37/37 |
| Reusable candidate CLI under python -O, 15:13:33 UTC | runner 3c51ec05; same app | 37/37 |

All dates are September 19, 2026. Environment: CPython 3.13.5, Chromium 144.0.7559.96, Linux x86_64/glibc 2.41. These are observed executions, not illustrative counts. The test set contains ten valid-file cases, seven invalid-encoding cases, twelve schema/limit cases and eight delayed-read/edit/reset/replacement/failure cases. Seven byte-pattern failures are not seven unrelated product defects.

The complete five JSON execution records are preserved in `SAVED_DRAFT_EXECUTION.json.xz`, not just their totals. Compressed SHA-256: `65773196092bdf30ca6c3362ef2c3dae728c25f268deb498d0d86757fb60f4e3`; uncompressed SHA-256: `19b85fc658dea4b38c6d05b576573df0a5a2cff0dcab60f2dba955f8d0c7cf36`. Historical publication labels inside those records describe the time of execution; they do not assert the present integration state.

```sh
python -c "import lzma,json,pathlib; d=json.loads(lzma.decompress(pathlib.Path('SAVED_DRAFT_EXECUTION.json.xz').read_bytes())); print({n:r['summary'] for n,r in d['runs'].items()})"
```

## Run the retained before/after control

Requires Python, Playwright, a supplied Chromium executable, and Node/git for the optional six patch-preparation tests. Nothing here installs software, calls a model service or contacts a live application. Copy this directory to a scratch location first: the explicit fixture generator writes `fixed_app.js` and `saved_draft_utf8.patch` next to itself.

```sh
python make_saved_draft_fix.py
python saved_draft_byte_review.py --variant original --output original-new.json
# The original command intentionally exits 1 and records seven failed cases.
python saved_draft_byte_review.py --variant fixed --output fixed-new.json
python -O saved_draft_byte_review.py --variant fixed --output fixed-optimized-new.json
python -m unittest -v test_patch_preparation.py
python -O -m unittest -v test_patch_preparation.py
```

The six preparation tests exercise exact patch application, normal/delayed Node File byte doubles, the native browser timing seam, refusal on unknown/ambiguous fixture text, preservation of a drifted checkout, and isolation of the saved-import change. They are not execution of the upstream parent-compiler suite. Normal execution was rerun 6/6 in this continuation; normal/optimized execution was also retained in the preceding review packet.

## Test a newly composed UI rather than trusting the old result

```sh
python saved_draft_byte_review.py \
  --candidate /path/to/workbench/app.js \
  --handoff /path/to/workbench/handoff.js \
  --importer /path/to/workbench/handoff_import.js \
  --html /path/to/workbench/index.html \
  --output composed-new.json
```

`--html` is optional. Without it, the retained fixture DOM is used. With it, script tags are removed before loading the supplied document; the selected actual helper/parser/app bytes are injected explicitly, and all browser network requests are aborted. This tests DOM behavior, not loaded CSS, native network, layout or accessibility. An incompatible UI API fails visibly; it is not guessed into a passing adaptation. The runner records the app, helper, parser and runner Git blob identities, DOM digest, browser version and actual state observations. Use new output filenames to preserve previous runs. Each scenario has a bounded execution wait; run unfamiliar application code in an appropriately isolated/supervised environment.

## Apply only the missing production seam

`saved_draft_complete.patch` contains the original production hunk plus the then-current native test-double changes. The reference base is `c4c305db7944cb305625836d4767d6abcc37ae36`. The generated app is `e570dcac8dd6bb6d35d5f8fede6c84b2220e8bb4`; original app `808a89401a7978c4897feb351aee231adcba8dd6`, helper `114e6c0bf9041a5dd178ed5b646e6b2069848d7e`, parser `20703283260781e87ef88c7ca0af17b380541f74`.

On a newer composition, port only the saved-file read: `await file.arrayBuffer()`; preserve generation/load-sequence/edit-revision guards; decode with `new TextDecoder('utf-8', {fatal:true})`; then call the existing strict saved-draft parser. Do not reject the U+FFFD glyph itself. Existing invalid-input handling must remain atomic. The native Node mocks need arrayBuffer and TextDecoder; the delayed browser-restore gate must intercept arrayBuffer instead of text. `prepare_native_fixture_patch.py` can generate the two native-test hunks from a complete original checkout only after checking their whole-file blob identities, and refuses a newer/ambiguous version instead of guessing.

The browser File API's text read uses UTF-8 decoding; the Encoding Standard exposes fatal error handling on TextDecoder. References checked September 19, 2026: [File API text()](https://w3c.github.io/FileAPI/#dom-blob-text), [Encoding TextDecoder](https://encoding.spec.whatwg.org/#interface-textdecoder). The concrete overwrite and repair results above come from executing this application, not from assuming the standard proves application correctness.

## Publication and limits

Canonical production integration: [#16145](https://github.com/woahwhattheheck/commons/pull/16145). Exact saved-import repair was first published in this continuation as [comment 5742921796](https://github.com/woahwhattheheck/commons/pull/16145#issuecomment-5742921796). Shared coordination: [Keystone thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824359432909). This directory is the existing [#16297 independent-review carrier](https://github.com/woahwhattheheck/commons/pull/16297), not another production app.

Source publication or merging this isolated review directory does **not** mean the production UI has received the repair. The current composed app must be read back and re-executed separately. No parent-compiler, native-network, hosted Actions, repository execution-authority, University findings, commercial approval, payment or submission result is claimed by these browser-logic checks. No scheduling or external outreach occurs.
