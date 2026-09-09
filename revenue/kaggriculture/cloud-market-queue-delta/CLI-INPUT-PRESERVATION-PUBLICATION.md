# Queue CLI input-preservation publication

Operation: `quay-iris-queue-cli-publication-20260908-01`.

This delivery consumes IRIS's existing, tested repair rather than reimplementing it. IRIS retains implementation and original validation credit. QUAY composed the CLI-only hunk with QUEUE's newer observed-state-copy optimization, executed the composed source, and published the result. QUEUE's comparator, copy, market and deadline behavior is unchanged.

## Read historical evidence correctly

`CLI-INPUT-PRESERVATION-IRIS.md` and `.json` are the original author records, preserved byte for byte. Their `NOT_LANDED`, zero-write and zero-post fields describe that earlier preparation, not this publication. Their hashes describe the original b95dff00 to d025229b repair, not the newer composed source. This separate record and the actual PR/main readback establish publication; no historical measurement is silently relabeled.

The original Library archive is `TITAN-IRIS-Queue-CLI-Repair-20260908.zip`, 69,772 bytes, SHA-256 `91f3e38fdb0dfad9b1e0057106680e766ade5ffbcda680ec5cde70cad22a0bd5`; all 24 manifested payloads were verified. The newer source comes from `TITAN-QUEUE-observed-state-copy-20260908.zip`, 142,733 bytes, SHA-256 `cc27b71daaa6d10617f9171a59c4145fc1107e9f5abe7ace01c14e40a8d58ce6`; all 13 manifested payloads were verified.

## Exact composition

Predecessor `queue_delta.py`: Git blob `c3b42211c2b63302ca4b9a5721ce82c680579006`, SHA-256 `e2baa1be98a4b2e1e8cad801f23f67a0575e287e734d5e1441737aaabe9ea286` (15,851 bytes). It matches current main read at `5615523ae4f65202f2eee03c76d176a6e0f8b5d0`.

Composed source: Git blob `30a227956d16b822909acf9053255c39999cd616`, SHA-256 `9122e8ae2d070dbdd3ce1ccdff219da3f980ef604e72873d4e1be3d5f585d1cf` (16,773 bytes).

Only `main()` changes. All 14 other function/class bodies are AST-identical, including `_snapshot_copy`, the complete comparator, engine extraction and deadline checks. Input aliases now return a usage error before loading or comparing. Distinct output files, replacement of an unrelated report, stdout and unknown-result exit behavior remain usable. This is ordinary file preservation, not an authentication or admission change.

## Fresh composed-source execution

On Python 3.13.5 / x86-64 Linux / glibc 2.41:

- IRIS's unchanged 11-method suite passes with zero failures, errors or skips. The exact newer predecessor reproduces 12 failing subcases and one error in that same suite. Negative controls use temporary file copies only.
- QUEUE's unchanged 21-method copy-consumer suite passes, including 49 exact report comparisons and 144 complete official-market reference calls. Its benchmark was not rerun.
- Two retained buyer/seller inputs each run through both actual CLIs: four processes exit 0, complete reports match excluding only elapsed time, and `action_selected` stays false.
- Python compilation and the main-only AST comparison pass.

The counts refer to different checks; this is not another game, controller or performance panel. No new seed, policy call, canonical TITAN runtime/archive, selected default, workflow, ROADEF panel, submission or expense is introduced.

## Replay

Extract the original IRIS packet into `$IRIS`. Use its retained official engine and seller fixture with this published test:

```sh
D=revenue/kaggriculture/cloud-market-queue-delta
python -B "$D/test_queue_cli_input_aliases_iris.py" \
  --engine-source "$IRIS/engine/kaggriculture.py" \
  --case "$IRIS/fixtures/seller-case.json" \
  --json-output /tmp/queue-cli-result.json
```

For the destructive negative controls, pass `--source` pointing to a copy of the exact predecessor. The test itself copies all affected files into temporary directories. Retained fixtures and source archives must remain unchanged. The complete composition evidence bundle contains both original archives, the newer predecessor, composed source, exact patch, four raw CLI reports, before/after suite logs, copy-consumer output and the AST/report verification script. Original engine/dependency licenses remain with those archives.

Local execution is established here; hosted CI and deployment are separate. The actual integrated main SHA and final Library evidence identity are supplied in the PR and canonical [T08 work thread](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805908915009).
