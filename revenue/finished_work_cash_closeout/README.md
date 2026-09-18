# Finished Work → Cash Closeout

Operation: `FINISHED-WORK-CASH-CLOSEOUT-ZCLL7Q4-20260916`.

This is a deterministic, offline owner-review compiler for already-finished work that may have a documented payment path. It exists to prevent two failures: calling finished work “revenue” without retained payment evidence, and sending duplicate payment/bounty requests when another request, DNR, duplicate payout unit, or Muse-elected owner already exists.

## Authority boundary

Every generated group and bundle carries these values as hard `false`:

```json
{
  "award_claim_authorized": false,
  "outbound_authorized": false,
  "payment_mutation_authorized": false,
  "provider_mutation_authorized": false,
  "revenue_recognition_authorized": false
}
```

`READY_FOR_MUSE_ELECTION` is only an internal next step. It means the retained evidence is complete enough to ask Muse for exact single-writer adjudication. It is **not** permission to contact a payer.

## Input contract

```json
{
  "schema": "finished-work-cash-closeout/v1",
  "items": [
    {
      "work_id": "frantic-120-pr-1423",
      "payer_key": "frantic",
      "opportunity_key": "bounty-120",
      "payment_unit_key": "pylon-1423",
      "route_key": "github:frantic/bounty-120",
      "currency": "USD",
      "advertised_amount_minor": 100,
      "advertised_reward_evidence": ["github:frantic/bounty-120#reward"],
      "eligibility_state": "ELIGIBLE",
      "eligibility_evidence": ["github:frantic/bounty-120#terms"],
      "completion_kind": "MERGED",
      "completion_receipts": ["github:sourcey/startup-credits/pr-1423#merged"],
      "provider_state": "MERGED",
      "provider_state_evidence": ["github:sourcey/startup-credits/pr-1423"],
      "payment_state": "UNPAID",
      "payment_state_evidence": ["provider:current-payment-state"],
      "payment_receipts": [],
      "prior_payment_request_receipts": [],
      "muse_owner": null,
      "dnr": false
    }
  ]
}
```

The four caller-supplied canonical keys `payer_key + opportunity_key + payment_unit_key + route_key` define a payout slot. Multiple work rows mapping to the same slot are emitted once and fail closed to reconciliation instead of generating duplicate request-ready actions.

Evidence tokens are retained references, not assertions independently verified by this tool. Human/upstream review remains responsible for external truth and freshness.

## States

- `PAYMENT_CONFIRMED`: `payment_state=PAID` plus retained payment receipt.
- `READY_FOR_MUSE_ELECTION`: advertised reward, eligibility, completion, payable provider state, and current unpaid evidence are retained, with no prior request, DNR, duplicate slot, or Muse owner.
- `WAIT_EXISTING_REQUEST`: a prior payment-request receipt already exists.
- `WAIT_PROVIDER`: provider/payment state is still submitted, review, pending, or otherwise non-payable.
- `EVIDENCE_GAP`: required evidence or current state is missing/unknown.
- `INELIGIBLE`: retained eligibility/provider state is terminally negative.
- `DNR_NO_SEND`: DNR is explicit.
- `COLLISION_RECONCILE`: duplicate payout slot or an existing Muse owner makes single-writer custody ambiguous.

## CLI

```bash
python revenue/finished_work_cash_closeout/closeout.py compile revenue/finished_work_cash_closeout/example_ledger.json /tmp/closeout
python revenue/finished_work_cash_closeout/closeout.py verify revenue/finished_work_cash_closeout/example_ledger.json /tmp/closeout
```

Compilation creates exactly `closeout.json`, `closeout.md`, and `receipt.json`. The receipt binds canonical input, JSON output, and Markdown output with SHA-256. The output directory must not already exist and files are created exclusively. A partial publication is left visible on failure rather than deleting a pathname that a same-authority writer could have replaced.

## Trust boundary

This is an offline evidence-consistency and collision-safety tool. The caller’s Python interpreter and filesystem authority are trusted. It does not claim cryptographic authenticity, provider freshness, same-account concurrent-writer immutability, or correctness of third-party facts. `verify` recomputes the expected bundle from the retained input and rejects byte changes.

## Validation

From repository root:

```bash
python -m py_compile revenue/finished_work_cash_closeout/closeout.py test_finished_work_cash_closeout.py
python -m unittest -v test_finished_work_cash_closeout.py
python -O -m unittest -v test_finished_work_cash_closeout.py
```
