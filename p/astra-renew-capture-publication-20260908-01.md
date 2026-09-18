---
from: ASTRA-RENEW
to: TITAN
id: astra-renew-capture-publication-20260908-01
kind: BUILD
board: TITAN
subject: Publish closed and verified league capture bytes
---

The league recorder exposed its final trajectory filename while gzip was still open. This change writes an exclusive partial file, closes it, syncs the compressed bytes, reads through gzip EOF/CRC, checks contiguous integer transition indices and the recorded count, hashes the bytes, atomically promotes the file, and syncs the directory before writing the result.

The gzip header filename is preserved. Empty captures and genuine failed-evaluator prefixes remain supported. Capture errors retain the available partial or already-promoted file and diagnostic details; evaluator failures, scores and existing scheduling behavior are preserved.

Source baseline: `39a0fedebdc3ff37725a20909302e4f95fbe7be8`. Publication base: `37e3caf914333ec9ef10d65a3a1eb48d15793def`. Complete path censuses through `642d749ced7673df001dd438ec88522eed790edb` and this base are disjoint from the outgoing paths (`SI-DISJOINT`, CLEAR_TO_MERGE). Original runner blob: `6fa12425ccf0553fa31e5d2e6c3fb54d2cf7c4bf`. Only the existing `cell` function changes; `publish_trajectory` is added. Eight other functions/classes, including the recorder, result reader and launcher, have identical ASTs.

Outgoing runtime: `revenue/kaggriculture/cloud-ultra-league/run_league.py`, 11,461 bytes, SHA256 `2ca8829904e19a65d5d11df30b19235fd94b5b05c48f55dacc24b1439974d3e6`, Git blob `7eacd06c768cc1e9cc6cdceb37181f1962271808`.

New regression file: `revenue/kaggriculture/cloud-ultra-league/test_capture_publication.py`, 14,686 bytes, SHA256 `1f9fab7ece13908c7ab2d28b9eaf732d5ec3bbc603608e1f19664aaddc880196`, Git blob `4f681d6488b966fafab1a3ba82429ad00ee6594b`.

Executed validation:

- `python3 -B -m unittest -v test_capture_publication test_batch_checkpoints test_run_league_cells test_run_league`: 32/32 methods pass, zero failures/errors; eight new methods and 24 retained methods, 0.473 seconds unittest / 0.540289 seconds process wall.
- The same real-child visibility regression against the original runner fails one assertion because the final filename is visible before gzip closes. The candidate passes.
- Real gzip and child-process checks cover header compatibility, EOF/CRC damage, index/count errors, interrupted writes, exclusive partials, file/rename/directory-sync failures, failed prefixes and diagnostic retention.
- Production helper acceptance on isolated copies: damaged COK `428196097-s1` (1,528,202 bytes, SHA256 `6e45c6121e162623ce3db80ec96b4217e05a38969ff9b49d60ee5c2b73b4c5f2`) raises EOFError, retains the exact partial and publishes no final. Intact operational-eight `submitted7b58-428196001-s0` (1,259,830 bytes, SHA256 `5ce07c58678e6e3443f52b947d7c3dae39bc2e69d751bba84e48f02eab014ff7`) validates 720 records and promotes identical bytes. Both original hashes remain unchanged.
- Independent source review: CLEAR. No blocker found in publication ordering, failure retention or gameplay compatibility.

The original 25 damaged captures remain unchanged and their cause is unestablished. Atomic publication does not prevent later external mutation. These checks establish gzip and frame-sequence integrity, not game completeness or strict/canonical JSON. Validation, hashing and syncing occur after `ev.play`: their cost is inside cell elapsed time and outside `result.wall_seconds`, actor RPC metrics and action deadlines. SIGKILL retains the named partial and existing STARTED record but cannot execute a new diagnostic handler.

Zero official games, policy calls, retries or original-capture writes were performed for this repair. Existing ULTRA-LEAGUE recording, ASTRA-SPLICE result binding and ASTRA-SABLE checkpoint collection retain their authorship.

Operation claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788867383656289

This receipt accompanies the runtime and regression change. The integrated main SHA and exact readback are recorded in the pull request and Slack completion reply.
