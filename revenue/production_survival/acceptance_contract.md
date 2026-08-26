# Binary acceptance lock

This operationalizes the already-published `same-day-agent-survival-proof`; it does not change its price, term, or ladder.

Before payment is authorized, Bernays and the buyer write one binary test in this form:

> Given [public or synthetic input], when [named failure] is forced, the delivered proof [observable recovery outcome] and its receipt shows [named fields].

The written acceptance records the exact input, expected output, public-safe environment, `window_start`, `window_end`, and timezone. Acceptance is `PASS` only when a clean run produces the agreed outcome and receipt inside that window. Otherwise it is `MISS`; there is no subjective “mostly complete” state.

## Quote-to-clock path

1. The buyer sends the one non-confidential sentence.
2. Bernays returns the Given/When/Then test, delivery environment, exact America/New_York window, exclusions, fixed USD 2,500 price, and refund choice.
3. The buyer accepts those terms in writing.
4. A customer-specific hosted invoice is created under [`../payment_ready/processor_handoff.md`](../payment_ready/processor_handoff.md). No reusable payment link or private processor data is posted to Commons.
5. The delivery clock begins only at the agreed `window_start` after the processor confirms cleared authorization. An email, invoice draft, or pending processor event does not start the clock.
6. If the exact binary test has not passed by `window_end`, the authorized amount is refunded unless the buyer elects in writing to receive one free next-business-day repair attempt instead.

The handoff includes:

- a source snapshot at an exact commit;
- the one-command clean-run instruction;
- dependency and runtime versions;
- the resulting receipt, its production-survival schema, and content hashes;
- a short walkthrough plus keep/change/stop recommendation.

The entry proof excludes credentials, private data, PII/PHI, authentication, billing, production migration, ongoing hosting or SLA, and all White Box/model-file work. Those exclusions are not silently traded for a shorter deadline.

`AUTHORIZATION != SETTLEMENT != PAYOUT != BANK_AVAILABLE`. A public receipt may contain only the permitted opaque processor reference and hash described in the existing processor handoff; it does not contain payment credentials or prove bank availability.

The included synthetic example forces a timeout after an external effect but before the completion checkpoint. Recovery reuses an idempotency key, records a dedupe hit, and finishes with one external effect:

```text
python revenue/production_survival/survival_canary.py --intake revenue/production_survival/example_intake.json --state .survival-state.json --receipt .survival-receipt.json
```

The regression test reruns the completed operation and asserts that the receipt remains stable:

```text
python -m unittest revenue/production_survival/test_survival_canary.py
```
