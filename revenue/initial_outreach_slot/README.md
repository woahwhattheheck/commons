# Initial outreach slot

This package closes the seconds-apart duplicate **first-contact** race across swarm workers.
It composes two landed controls:

- `revenue.commercial_opportunity_custody`: current WHOLE / bounded `outreach` custody;
- `tools.outbound_send_guard.capability_lease`: v2 live Git-ref ownership plus private-capability possession.

The terminal exclusion key is the canonical commercial opportunity, not an offer or price alias. Two workers describing the same pursuit as `$5k validation` and `$7.5k validation` therefore race one immutable ref:

```text
refs/tags/initial-outreach-v1/<sha256({schema, action, canonical opportunity})>
```

## Provider-bound execution, not a bearer receipt

`execute_initial_outreach(...)` accepts a zero-argument `send_once` callback that performs exactly one provider mutation. The callback is invoked only after all of these conditions hold in the same invocation:

1. live custody says the exact actor/operation owns WHOLE or `outreach`;
2. the v2 lease receipt is structurally valid and its repo/buyer/claimant bind to that opportunity/actor;
3. `capability_lease.verify_possession(...)` proves the private capability and current live v2 ref/tag;
4. a second custody read proves no transfer/release occurred during lease verification;
5. the canonical opportunity slot is absent;
6. this invocation creates the annotated audit tag and wins create-once creation of the canonical slot ref (or immediate same-call readback proves an indeterminate create created this exact tag);
7. a third custody read proves no transfer/release raced slot consumption.

Only then is `send_once()` called, synchronously and exactly once by this boundary.

No serializable result ever contains `external_send_authorized=true`. The callback result itself is not stored; only a SHA-256 of its `repr` is retained as local correlation evidence. Durable tag metadata also fixes `external_send_authorized=false` and contains no raw capability, recipient address, subject/body, price, provider message ID, acceptance, payment, or revenue assertion.

If `send_once()` raises—or the process dies after the slot is consumed—the slot remains consumed. The result is reconciliation/DNR-only. Calling this module again never invokes another initial-send callback. This deliberately prefers a potentially lost outreach attempt over duplicate first contact.

## Result semantics

- `PROVIDER_CALLBACK_RETURNED`: slot consumed and callback returned normally. This does **not** infer provider delivery/completion.
- `SEND_OUTCOME_UNKNOWN`: callback was invoked but raised. Slot remains consumed; no retry authority.
- `HOLD`: callback was not invoked. `HOLD_ALREADY_CONSUMED` means a prior invocation already owns/burned first contact.

Every result has:

```json
{"external_send_authorized":false,"provider_send_completed":false,"replay_or_retry_authorized":false}
```

`inspect_initial_outreach(...)` is read-only DNR/reconciliation evidence. It validates live slot ref -> annotated tag -> metadata/target/tagger and never authorizes send.

## Validation

```bash
python -m py_compile revenue/initial_outreach_slot/slot.py revenue/initial_outreach_slot/test_slot.py
python -m unittest -v revenue.initial_outreach_slot.test_slot
python -O -m unittest -v revenue.initial_outreach_slot.test_slot
```

Hostiles cover price/offer aliasing, same-holder replay, copied/wrong private capability, buyer/repo/claimant mismatch, custody transfer before and after slot consume, concurrent existing ref, provider uncertainty, same-call indeterminate recovery, callback exception burn-without-retry, raw-capability/result privacy, receipt tamper, and strict inspection of tampered/duplicate-key metadata.
