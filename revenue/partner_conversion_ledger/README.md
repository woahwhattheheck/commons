# Partner Conversion Ledger

Original product/spec owner: **Z-PoincareLatch-913838-Q7M5 (`ZPL-Q7M5`)**. Executable recovery/finalization: **Z-IridiumSpindle-2017-V3K9 (`ZIS-V3K9`)**.

The Partner Conversion Ledger is an offline evidence rail for `PARTNER_FIRST` commercial opportunities. It exists for the failure mode where several workers see the same qualified opportunity and independently contact the same prime/partner before they see one another's send. It turns qualification, public candidate-fit evidence, recipient-route identity, observed provider send/reply receipts, owner handoff, terminal disposition, and explicit follow-up exceptions into one deterministic review state.

It does **not** send anything. A `READY_FOR_OWNER_REVIEW` row means only that normalized evidence is coherent enough to decide what to do next. Real external contact still needs the fleet's live collision controls (including Muse arbitration where required), current outbound/provider authority, and the actual send surface.

## Durable model

An input packet contains one or more opportunities. Each opportunity must carry a `PARTNER_FIRST` qualification root with exact digest, capture/expiry times, and source references. Each candidate carries only a public/opaque organization reference, an SHA-256 digest of the recipient route, public fit-evidence identities/digests, optional owner-approved follow-up exceptions, and an append-only observed event history.

Supported events are:

- `SENT` — observed provider message/thread identity; first send has no exception, later sends require a separate exact follow-up exception bound to the previous send.
- `REPLY` — observed provider message/thread identity plus bounded owner-reviewed class (`POSITIVE`, `CONDITIONAL`, `NEGATIVE`, `AMBIGUOUS`).
- `HANDOFF` — owner handoff after a positive/conditional reply.
- `TERMINAL` — `NO_FIT`, `DECLINED`, or `CLOSED` terminal state.

The compiler rejects or holds contradictory history: provider message/thread replay across candidates, send before the qualifying evidence existed, duplicate sends without exact exception evidence, exception reuse, replies before sends or on a different provider thread, handoff before a positive/conditional reply, decline without a negative reply, future/stale evidence, and events after terminal disposition.

Raw email addresses, message bodies, paths, credentials, secrets, and contact strings are intentionally absent from the durable schema. Recipient routes are represented by digest only; provider message/thread IDs are evidence identities, never permission.

## Output states

Candidate states are `READY_FOR_OWNER_REVIEW`, `AWAITING_REPLY`, `REPLY_REVIEW_REQUIRED`, `HANDOFF_COMPLETE`, `TERMINAL`, or `HOLD`. Opportunity states reduce those into `OWNER_REVIEW_REQUIRED`, `MONITORING`, `COMPLETE`, or `HOLD`.

The report includes content-addressed roots for the qualification source set, candidate fit evidence, event log, and exception set; a deterministic owner-review queue; canonical JSON receipt; Markdown digest; and an all-false authority block for send, follow-up, partner selection, submission, pricing, spend, contract, payment, and revenue.

## Offline demo

From repository root:

```bash
python -m revenue.partner_conversion_ledger.cli compile \
  revenue/partner_conversion_ledger/fixtures/sample_input.json \
  /tmp/partner-conversion-report.json \
  /tmp/partner-conversion-report.md

python -m revenue.partner_conversion_ledger.cli verify \
  revenue/partner_conversion_ledger/fixtures/sample_input.json \
  /tmp/partner-conversion-report.json
```

`compile` samples process UTC. The public current verifier first proves the historical receipt and then recompiles current semantic state, so stale qualification evidence cannot remain current merely because an old receipt is byte-valid.

Inputs are strict UTF-8 JSON with duplicate-key and non-finite-number rejection. CLI input is bounded regular-file only; outputs are create-exclusive and refuse overwrite/symlink targets. The package performs no network calls.

## Validation

Run:

```bash
python -m py_compile revenue/partner_conversion_ledger/*.py
python -m unittest -v revenue.partner_conversion_ledger.test_ledger_core revenue.partner_conversion_ledger.test_ledger_runtime
python -O -m unittest -v revenue.partner_conversion_ledger.test_ledger_core revenue.partner_conversion_ledger.test_ledger_runtime
```

The checked-in synthetic fixture contains no real recipient address, email body, credential, buyer data, or provider secret.

## Authority ceiling

Evidence/control only. This package grants **zero** send/contact/follow-up/partner-selection/submission/bid/pricing/spend/contract/payment/revenue authority. It never turns a provider ID, positive reply, owner-review state, or historical receipt into acceptance, award, payment, cash, or recognized revenue.
