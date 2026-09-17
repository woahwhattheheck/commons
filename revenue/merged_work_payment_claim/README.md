# Merged-work payment claim packet compiler

This package turns retained evidence for advertised compensation plus exact merged/accepted work into a deterministic **payment-request draft packet**. Its positive terminal state is deliberately narrow:

`READY_FOR_MUSE_PAYMENT_REQUEST`

That state means the evidence supports asking the swarm's Muse single-writer arbiter to elect one sender for a direct payment request. It does **not** resolve a recipient, authorize a message, create an invoice, prove money is due or paid, establish a receivable, or recognize revenue.

## Why this is not `accepted_work_to_cash_reconciler`

`revenue/accepted_work_to_cash_reconciler` is the broad operational queue above the revenue funnel: it composes acceptance, route/contact and cash-related evidence to choose the next owner action for many kinds of opportunities. This package is intentionally narrower and downstream-facing: it binds one exact merged work item to one advertised compensation record, one acceptance record, current eligibility, current payment-status evidence, and prior payment follow-ups, then emits the exact **payment-request artifact** or a reason not to ask yet. It never mints a recipient/route and therefore cannot substitute for the reconciler or Muse.

## Input

Schema: `TJL_MERGED_WORK_PAYMENT_CLAIM_V1`.

Required evidence includes:

- exact `owner/repo`, PR number, merged commit SHA, deliverable SHA-256 and retained merge source;
- optional advertised compensation object (`null` becomes `HOLD_NO_COMPENSATION`), with currency, integer minor amount, advertisement source and optional expiry;
- optional acceptance object (`null` becomes `HOLD_NO_ACCEPTANCE`) independently binding the same repo/PR/commit;
- explicit `ELIGIBLE | INELIGIBLE | UNKNOWN` evidence;
- bounded immutable follow-up events;
- explicit retained `PAID | UNPAID | UNKNOWN` payment-status evidence;
- owner-authored maximum status age and follow-up cooldown;
- a process/caller-supplied `evaluation_at` bound into the report and receipt. It is not read from the packet.

The compiler refuses duplicate JSON keys, floats/non-finite values, unsafe integers, boolean-as-integer aliases, lone surrogates, future evidence, changed-scope acceptance, reminted duplicate follow-up economics and malformed hashes/timestamps.

## States

- `READY_FOR_MUSE_PAYMENT_REQUEST`
- `HOLD_ALREADY_PAID`
- `HOLD_COOLDOWN`
- `HOLD_INELIGIBLE`
- `HOLD_STALE`
- `HOLD_NO_COMPENSATION`
- `HOLD_NO_ACCEPTANCE`
- `HOLD_EVIDENCE`

Fresh `UNKNOWN` eligibility or payment status fails closed as `HOLD_EVIDENCE`. A prior retained `PAID` status always stops a new request. A prior request inside the owner-authored cooldown stops another request. Compensation is valid through its exact `expires_at` second and stale only after it.

## Artifacts

Compilation emits, create-exclusively:

- `payment-claim.report.json`
- `payment-claim.md`
- `payment-claim.receipt.json`

The Markdown contains a direct request draft only in the READY state. Even then, recipient and route are `null` and the artifact tells the executor to obtain a **fresh Muse election + last-inch contact/payment recensus** before any external message.

The semantic verifier recompiles from the original input plus `evaluation_at` and compares canonical serialized bytes for report and receipt. This intentionally rejects `false -> 0` / `true -> 1` artifact aliases even though ordinary Python container equality may consider those values equal.

## Authority ceiling

Every report hard-codes all of these to false:

- send authorization
- Muse authorization
- provider action authorization
- payment authorization/proof
- invoice creation
- receivable assertion
- revenue recognition
- contract/accounting conclusion

No network I/O exists in the package.

## CLI

```bash
python -m revenue.merged_work_payment_claim.core compile \
  revenue/merged_work_payment_claim/example.json /tmp/payment-claim \
  --evaluation-at 2026-09-17T20:00:00Z

python -m revenue.merged_work_payment_claim.core verify \
  revenue/merged_work_payment_claim/example.json \
  /tmp/payment-claim/payment-claim.report.json \
  /tmp/payment-claim/payment-claim.md \
  /tmp/payment-claim/payment-claim.receipt.json \
  --evaluation-at 2026-09-17T20:00:00Z
```

## Tests

```bash
python -m py_compile revenue/merged_work_payment_claim/*.py test_merged_work_payment_claim.py
python -m unittest -v test_merged_work_payment_claim.py
python -O -m unittest -v test_merged_work_payment_claim.py
```
