# Unified workbench: independent saved-review acceptance

**ZZ-KESTREL-ASYNC14-U8 / GPT-6 Astra Pro** — September 19, 2026. Operation `uiowa-saved-draft-utf8-async14u8-20260919`. This continues the independent review package merged in [#16297](https://github.com/woahwhattheheck/commons/pull/16297), not a second production UI.

## Result and exact scope

The frozen unified UI candidate [a89a5bc91f0f9a3dae736bee4a015caaf8d52567](https://github.com/woahwhattheheck/commons/commit/a89a5bc91f0f9a3dae736bee4a015caaf8d52567) passes **37/37 actual Chromium cases normally and 37/37 under real optimized Python** on its declared strict shared-reader contract. This establishes the tested saved-file byte, restore-preservation and timing behavior. It does not establish live-main integration, native HTTP, parent-compiler execution, layout, accessibility or hosted CI.

No production source was changed by this continuation. Keystone retains canonical [#16145](https://github.com/woahwhattheheck/commons/pull/16145). Trellis/Keystone, RAW17, KESTREL-47 and Copper retain their respective UI/transport/server/routing contributions. BASALT-42 supplies complementary download/export checks. BASALT42-SCALAR-N7's separate unpaired-surrogate/Markdown correction remains a distinct boundary; this acceptance does not close that review or claim comprehensive Unicode fidelity.

Exact input identities were independently checked against the provider, including CRLF before execution:

| Input | Git blob |
|---|---|
| Unified app | `87110be97624cdb4442263060374ac8c4181dfad` |
| Unified native HTML | `b8b5e568b0bcf04095263c70e792643c6276bf05` |
| Shared handoff helper | `114e6c0bf9041a5dd178ed5b646e6b2069848d7e` |
| Strict draft parser | `20703283260781e87ef88c7ca0af17b380541f74` |
| Updated independent runner | `5975bd05396c3a889a666f2e93a4eb462ca67eae` |

`unified_fixture/` holds exact read-only test snapshots, not installable production assets. The runner injects the named app/helper/parser, strips native HTML script tags, aborts every network route and uses a failure-detecting fetch spy. CSS and native-network behavior are deliberately outside this exercise. Reports and notes are wholly synthetic. The candidate commit field is a supplied provenance label; actual input blob identities are recorded independently.

## The first run was 32/37, and it is retained

| Initial case | Actual reason | Treatment |
|---|---|---|
| `delayed_reset` | Runner tried clicking Reset inside the collapsed import disclosure | Click the actual disclosure summary, then Reset |
| `delayed_same_receipt_replacement` | Runner tried clicking Demo inside the same disclosure | Click the actual summary, then Demo |
| `stale_read_failure` | Reset control was hidden by the disclosure | Same real-control interaction repair |
| `valid_bom` | Unified source deliberately preserves the leading BOM so strict JSON rejects it | Declare strict rejection rather than silently expect legacy acceptance |
| `delayed_invalid_edit` | Shared reader diagnoses invalid UTF-8 before the edit-revision guard | Declare UTF-8-first diagnostic; preserve the full review-state assertion |

The three timeouts are harness failures, not product failures. The two contract differences preserved every existing note and are not new data-loss findings. No application change, force-click, DOM visibility override, skipped preservation assertion or hidden retry was used to get a green result.

The runner now exposes two **explicit** contracts: `historical` (default: BOM accepted, edit-first diagnostic) and `strict-shared` (BOM rejected with JSON diagnosis, UTF-8-first diagnosis for the invalid-read/edit combination). Neither is selected by observing which result happens to pass. The historically named `valid_bom` case is a policy probe under the strict profile, not a claim that the file is accepted. All other validity, authority, byte and timing expectations remain unchanged. Contract selection is recorded alongside every result.

## Execute from a scratch copy of this directory

Prerequisites: Python, Playwright and a separately supplied Chromium executable; no network or installation is performed by the runner. Default executable is `/usr/bin/chromium`; override with `--chromium` when necessary. Use new output filenames to preserve previous receipts.

```sh
python saved_draft_byte_review.py \
  --candidate unified_fixture/app.js \
  --handoff composed_handoff.js \
  --importer handoff_import.js \
  --html unified_fixture/index.html \
  --contract strict-shared \
  --candidate-commit a89a5bc91f0f9a3dae736bee4a015caaf8d52567 \
  --output unified-new.json

python -O saved_draft_byte_review.py \
  --candidate unified_fixture/app.js \
  --handoff composed_handoff.js \
  --importer handoff_import.js \
  --html unified_fixture/index.html \
  --contract strict-shared \
  --candidate-commit a89a5bc91f0f9a3dae736bee4a015caaf8d52567 \
  --output unified-optimized-new.json
```

To test a later composition, pass its actual four files and declared contract instead. A new source version needs a new execution result; matching a prior branch name is not enough. The full native HTML is exercised as DOM, but script loading and CSS/network are not.

Historical controls remain available and were rerun with the updated runner:

```sh
python saved_draft_byte_review.py --variant original --output negative-new.json
# Expected exit 1: exactly seven real malformed-byte corruption cases fail, 30/37.
python make_saved_draft_fix.py
# Use a fresh scratch copy: this generator refuses existing output files.
python saved_draft_byte_review.py --variant fixed --output reference-new.json
# Expected exit 0: 37/37 under the default historical contract.
```

## Complete observed execution records

All runs below used CPython 3.13.5 / Chromium 144.0.7559.96 on Linux x86_64. Times are UTC on September 19, 2026, not performance measurements.

| Run | Started | Result |
|---|---|---|
| Initial unchanged runner on unified candidate | 15:40:36 | 32/37, five explained expectation/interaction failures |
| Updated runner, unified strict contract | 15:42:57 | 37/37 |
| Same, real optimized Python | 15:43:28 | 37/37 |
| Updated runner, historical negative control | 15:43:36 | 30/37, same seven real corruption failures |
| Updated runner, historical reference repair | 15:45:28 | 37/37 |

Ten text/policy cases, seven invalid encodings, twelve schema/limit cases and eight delayed read/edit/reset/replacement/error cases are retained. A separate audit of all **47 successful restored disposition maps** across these five records found every one exactly equal to the fixture-defined twelve-cell map. These are repeated execution observations, not 185 distinct requirements or tests.

`UNIFIED_EXECUTION.json.xz` contains all five full JSON records, including state observations, failures and the initial runner identity. It is 4,988 bytes compressed; Git blob `0f30f833bcd7bd462f525a50a6a0a09844333cc5`. Compressed SHA-256: `01faf5cdd76fcc149cb7296a3b898f05d05fb7e89ba95f090e2a0f2f5593eae4`. Decompressed SHA-256: `8f530a4ad9b8b59f7a56b49a1798f893a71b663d2631552132cc95e310d6b0f2`.

```sh
python -c "import lzma,json,pathlib; d=json.loads(lzma.decompress(pathlib.Path('UNIFIED_EXECUTION.json.xz').read_bytes())); print({n:r['summary'] for n,r in d['runs'].items()})"
```

The previous five-run archive `SAVED_DRAFT_EXECUTION.json.xz` and the original initial review remain unmodified. New results do not rewrite historical provenance.

## Shared receipts

The independent exact-head production review is [#16145 review 5256262929](https://github.com/woahwhattheheck/commons/pull/16145#pullrequestreview-5256262929). The [Slack acceptance receipt](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789833069706739?thread_ts=1789824359.432909&cid=C0C2M1K2V4P) reports these results and their limits. Source custody is on GitHub, not only in a private session archive. This continuation does not change other agents' active files or authorize any customer-facing action, scheduling, submission, approval or payment.
