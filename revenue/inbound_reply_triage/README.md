# Inbound reply triage

`revenue/inbound_reply_triage` turns retained commercial-contact events into a deterministic **owner-review queue**. It exists to protect warm replies from getting buried while preserving the single-writer/Muse collision discipline.

## Contract

Input binds every lane to an exact `org_key × route_key × domain × purpose_key × thread_key`. Events are chronological and evidence-referenced. `SENT` requires a fresh prior `MUSE_SELECTED`; a repeat send in history additionally requires an intervening human reply. Unsolicited genuine inbound can be represented without a prior send.

The compiler distinguishes:

- `NEW_HUMAN_INBOUND`
- `RESPONSE_READY_OWNER_REVIEW`
- `AUTO_REPLY`
- `BOUNCE`
- `REJECTION`
- `WAITING_EXTERNAL`
- `DNR`
- `COLLISION_HOLD`
- `MUSE_REQUIRED`

A drafted response becomes `RESPONSE_READY_OWNER_REVIEW` only with an active, evidence-bound one-writer lease. An expired/missing lease fails closed to `COLLISION_HOLD`. DNR/collision/bounce/rejection evidence is never converted into a human reply. Same-second mutually exclusive status evidence fails closed instead of using list position as authority.

`evaluation_at` and `stale_after_minutes` produce deterministic reply age/staleness. The owner-review queue prioritizes human inbound first, with older human replies first within a state.

## Authority ceiling

This package **does not send anything**. It cannot select Muse, contact a buyer/partner, assert acceptance, create a contract or invoice, move money, establish a receivable, or recognize revenue. Every such authority bit is hard false in compiled output. For any state that may eventually need an external response, `next_gate` remains `MUSE_REQUIRED_BEFORE_ANY_SEND`.

The receipt is not an external-provider attestation. It binds exact source and compiled packet bytes; `verify_triage()` recompiles and rejects tampering.

## Test

```bash
python -m unittest test_revenue_inbound_reply_triage.py -v
python -O -m unittest test_revenue_inbound_reply_triage.py -v
python -m py_compile revenue/inbound_reply_triage/core.py test_revenue_inbound_reply_triage.py
```
