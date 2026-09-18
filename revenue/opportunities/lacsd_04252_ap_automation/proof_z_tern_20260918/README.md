# LACSD 04252 — recovered independent proof

Operation: `LACSD-04252-ZTERN-PROOF-RECOVERY-20260918`.

This self-contained directory recovers Z-Tern's previously session-local independent tests, exact source closure, replay runner, and offline report generator for Commons PR #15865. It is an internal engineering artifact, not a prospect destination, new AP product, accepted engagement, or submission. No new workflow or scheduled job is introduced.

Original product credit: **Sol-Z**. Refresh/source credit: **Z-Quoin-6F2**. Current-source donor: **Z-QuasarLatch-2112**. Independent tests/report/recovery: **Z-Tern / GPT-6 Astra Pro**. Existing Devin-Local and Z-Basalt execution/review contributions are not replaced by this donor.

## Snapshot versus active source

`lacsd-15865/` is a retained five-file closure from exact head `d6ba9099718fab8b308daeab7c7b57d1e97aa786`, not the current product working directory. Original Git blobs are reused unchanged. The runner checks all five before and after executing the original tests. The generator checks them before creating the report. Changes to current product source do not silently change this snapshot; a new generation needs explicit pins and evidence.

The preserved source README and generated report contain historical status, deadline, and outreach/Muse language from that snapshot. They are **not current operating instructions or fresh public-source verification**. The report's no-remote-mutation statements refer to its read-only execution/generator, not the later GitHub/Slack publication. Current owner instructions and the active shared collision-prevention system govern future outreach. No outreach is performed here.

## Reproduce in any clean directory

From this directory, using the intended interpreter:

```sh
python run_exact_proof.py --output /tmp/lacsd-original-proof-new --worker YOUR_SEAT --execution-context YOUR_ACTUAL_CONTEXT
python -m unittest discover -s independent-tests -p test_lacsd_independent.py -v
python -O -m unittest discover -s independent-tests -p test_lacsd_independent.py -v
python build_demo_report.py --output /tmp/lacsd-report-new
```

Both output directories must be new. No network, credentials, paid service, database, invoice upload, Oracle connection, or buyer data is needed. Python's standard library suffices. The report command regenerates HTML, CSV, JSON, and a checksum manifest for all eleven supplied cases. It displays historical test counts rather than running tests itself; run the test commands separately before claiming a new execution result.

## Observed execution

Fresh recovery replay on September 18, 2026 at 06:38:51–06:39:03 UTC used cloud Linux x86_64, **CPython 3.13.5**. Compilation exited 0; original suite passed **34/34 normally and 34/34 under real `python -O`**. The subsequent independent suite passed **15/15 normally and 15/15 under real `-O`**. The runner's raw receipt is retained in `execution_receipt.json`; it retains its unspecified-operator defaults without retroactively changing the script output. Z-Tern separately attests that this was the session cloud, not the owner's machine.

The independent suite covers 2,048 combined gate states and 20,000 accuracy-boundary cases per mode, exact money and subsecond 48-hour boundaries, boolean/integer alias rejection, source URL/time binding, deadline expiry, authority outputs, and semantic-receipt tampering. Replays do not increase the number of distinct tests.

This is **source-closure proof**, not full-repository integration, hosted CI, or Python 3.12 proof. No active product behavior is modified. Existing workflow-budget and carrier finalization work stays in its existing lane; this recovery adds no active workflow and does not raise the cap.

## Commercial and evidence interpretation

The compiler evaluates supplied facts. Passing these tests is not measured invoice extraction, live vendor matching, Oracle synchronization, provider authentication, planholder eligibility, a signed contract, receivable, revenue, or cash. `verify_evidence` verifies semantic recompilation, not raw-input authenticity or complete input identity. Equal changes to invoice and PO totals can leave the same semantic result; acceptance-text changes can preserve the projection. The independent suite explicitly documents this boundary.

The existing $5,000 specialist workshare was `PROPOSED_NOT_ACCEPTED` in the retained manifest. This package introduces no new quote or financial claim. Its purpose is to make the existing AP/UAT workshare replayable for the owner and peers, without leaving reusable work trapped in a chat session.

Internal evidence publication: https://github.com/woahwhattheheck/commons/pull/15865#issuecomment-5726188950
Owner execution-request thread: https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1789698040246119

## Recovered source identities

| File | Git blob SHA-1 |
|---|---|
| lacsd-15865/lacsd_04252.py | a5f2f9730724f81fc0202519601e02fe63340dd6 |
| lacsd-15865/test_lacsd_04252.py | bff86c95ea65e242c5c2bf8a3673651bb00f0250 |
| lacsd-15865/fixtures/manifest.json | a11113306aa62274e17e57f48f5d7056bfe9c558 |
| lacsd-15865/fixtures/ap_cases.json | 4b5d070864bb6db3ebae439894283d216c965bd7 |
| lacsd-15865/README.md | 5249a545558c5a78ae5e725193f3e1aee4d1cb68 |
| independent-tests/test_lacsd_independent.py | aa909b9338e4bcb1cd410e56cf9541ed453ce7b1 |
| run_exact_proof.py | d24b99dd9feb01970664f83699a405a65f4b25ef |
| build_demo_report.py | b7d3915d5b6032689509344ae27074d97666b474 |
