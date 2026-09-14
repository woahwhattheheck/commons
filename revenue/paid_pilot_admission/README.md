# Paid Pilot Admission Gate

`paid_pilot_admission` is a deterministic, offline evidence gate for the moment between **a proposed commercial offer** and **an owner's decision to admit delivery work**.

It exists because a sales reply, a payment-looking screenshot, or a partially funded arrangement must not silently become authority to start free or expanded work. The compiler binds one exact offer to buyer-acceptance evidence and settled-funding evidence, then produces either `READY_FOR_OWNER_WORK_ADMISSION` or named HOLD states.

## What it binds

An offer declares:

- opaque `offer_id` and `buyer_scope`;
- exact currency, total price, and admission funding amount in integer minor units;
- sorted scope and acceptance-criteria lists;
- issuance / expiry times;
- maximum age of funding evidence.

Acceptance must repeat the exact offer ID and SHA-256 digest. Funding evidence must repeat the same binding, currency, and meet or exceed the admission amount. Only `CAPTURED` and `ESCROW_FUNDED` count as settled evidence; `AUTHORIZED`, `PENDING`, invoice creation, payment-link creation, or promises do not.

The funding record includes a `source_authority` label plus an evidence SHA-256. **This package does not authenticate that source.** The owner/integration must obtain the funding observation from an independently trusted provider readback. A caller-supplied hash is integrity metadata, not proof that money moved.

## Authority ceiling

The strongest state is deliberately `READY_FOR_OWNER_WORK_ADMISSION`, not `WORK_STARTED`, `PAID`, `ACCEPTED`, or `REVENUE`.

This package never:

- contacts a buyer;
- creates or accepts a contract or signature;
- calls Stripe, a bank, escrow service, or other payment provider;
- charges, captures, refunds, or moves money;
- mutates CRM/calendar/project/provider state;
- starts delivery work;
- claims buyer acceptance, payment, cash, or recognized revenue.

Every receipt fixes all of those external-authority bits to `false`.

## Currentness and replay

`evaluate()` must receive a trusted current process time. It rejects expired offers, future-dated acceptance/funding observations, acceptance recorded after the funding observation, stale funding evidence, partial funding, and transplanted offer bindings.

Receipts are **historical immediately after evaluation**. `verify()` recomputes the historical receipt using its frozen `evaluated_at` timestamp; it proves receipt integrity only. Before an owner admits work, run a fresh `evaluate()` against current evidence.

## CLI

From the repository root:

```bash
python -m revenue.paid_pilot_admission.cli evaluate packet.json --json-out receipt.json --markdown-out receipt.md
python -m revenue.paid_pilot_admission.cli verify packet.json receipt.json
python -m revenue.paid_pilot_admission.acceptance
python -m unittest revenue.paid_pilot_admission.tests.test_gate -v
python -O -m unittest revenue.paid_pilot_admission.tests.test_gate -v
```

Exit codes: `0` ready/verified, `2` malformed input, `3` valid packet held, `4` receipt verification failure.

## Commercial use

Use this after a buyer or prime has accepted an exact scoped offer and after funding evidence is available from a trusted source. It protects margin and prevents a generic “yes” from becoming authorization for unpriced scope creep. It is buyer-neutral and does not supersede product-specific delivery, legal, accounting, tax, or payment controls.
