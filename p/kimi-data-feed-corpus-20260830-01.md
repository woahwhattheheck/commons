# Board feed corpus sample + license decision package — 2026-08-30

State: `LANDED` only when this file is read from current `main`; a branch copy is a candidate.

Bryce, 2026-08-30 00:44 EDT: "We have unique data as well!" The data road (#5526) landed with an
inventory page and one corpus candidate, both blocked at the same wall: the repository has no root
license, so reuse rights are `NOASSERTION` and transfer stays `BLOCKED_LICENSE_REQUIRED`. This lane
builds the second corpus — the genuinely unique asset — and stages the one decision only the rights
holder can make.

## What landed

- `revenue/data/board_feed_sample_20260830.json`: the frozen sample — the live board feed's 500 most
  recent rows at fetch time (2026-08-28T20:40:08Z → 2026-08-30T05:17:23Z), copied verbatim. 622,325
  bytes. This is the multi-seat institution record: 24 distinct seats (owner, tools, and multiple
  model families) coordinating work in public — the chorus era included.
- `revenue/data/board_feed_corpus.json` + `.schema.json`: the fail-closed manifest. Checksums pinned
  (git blob SHA + SHA-256 + byte count), nine-rule secret/PII scan PASS_ZERO_HITS, sensitivity review
  PASS (public seat pseudonyms and raw Slack member IDs already visible on the public board; no
  credentials, emails, phones, customer material, or private paths), window statistics recorded from
  the bytes. License stays `NOASSERTION`; release stays `BLOCKED_LICENSE_REQUIRED`.
- `host/board_feed_corpus.py`: stdlib-only validator. Re-hashes the sample, recomputes the window
  statistics from the bytes, re-runs the scan, and refuses drift, license promotion, release
  readiness, or invented commercial truth. CLI: `validate --root`.
- `revenue/data/license_decision_package.md`: the rights-holder one-pager. Three staged options
  (CC0 / CC BY 4.0 / Commons Commercial Data License) plus the recommended split (CC BY on the public
  record, commercial license as the paid instrument), and the exact unblock mechanics. The package
  decides nothing; the rights holder's one word does.
- `test_board_feed_corpus.py`: schema contract, exact entry set, blob/SHA-256/window drift
  fail-closed, scanner positive controls, review completeness, license-promotion refusal,
  release-readiness refusal, truth-invention refusal, CLI round-trip.
- `data-license.html`: third inventory card for the board feed sample, same blocked-state pattern.

## Truth boundary

A frozen, checksummed sample is not a license, a buyer, an agreement, a delivery, or cash. The
license decision belongs to the rights holder and is staged, not made. Collected cash remains USD 0.
No contact, transfer, or sale is claimed by this lane.

— KIMI (K3)
