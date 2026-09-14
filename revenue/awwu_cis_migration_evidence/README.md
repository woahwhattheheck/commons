# AWWU / Utility CIS Migration Evidence Workshare

Offline evidence compiler for a **paid migration / integration validation subcontract** around a qualified utility-CIS prime.

The initial opportunity profile is Municipality of Anchorage / Anchorage Water and Wastewater Utility RFP `2026P044`. Public procurement metadata describes a replacement Customer Information System spanning utility billing, customer service, mobile workforce management, cashiering, implementation, data conversion, integration, testing, training, stabilization, and support. The product is generic enough to reuse for a different utility-CIS pursuit by replacing the source-bound input.

## Commercial boundary

A compiled packet keeps the workshare at `PROPOSED_NOT_ACCEPTED`. It can become `READY_FOR_OWNER_TEAMING_REVIEW` only when the opportunity source is current, the deadline is open, dataset row/key/control-total reconciliation is exact, every declared required interface has round-trip/retry/rollback/duplicate-effect PASS evidence, the cutover rehearsal is fully evidenced, and all external authority flags are false.

It does **not** authorize a provider send, claim a prime participates, contact the buyer, submit to BidExpress, sign a contract, charge, treat a payment route as payment, or recognize revenue.

## Checks

- current, hash-bound opportunity/source metadata and deadline;
- fixed price, duration, deliverables, acceptance criteria, and exclusions;
- per-dataset row counts, key-set digests, control totals, duplicate/missing/unexpected/rejected rows;
- required-interface contract and test receipt binding;
- round-trip, retry idempotency, rollback, and duplicate-effect checks;
- dry-run/reconciliation/rollback/restart cutover evidence;
- immutable receipt digest and exact input binding;
- historical receipt replay plus verifier-owned current revalidation.

## CLI

```bash
python -m revenue.awwu_cis_migration_evidence.compiler compile input.json receipt.json
python -m revenue.awwu_cis_migration_evidence.compiler verify input.json receipt.json
python -m revenue.awwu_cis_migration_evidence.compiler render input.json receipt.json brief.md
```

`compile` and `render` use create-exclusive outputs and refuse overwrite.

## Price hypothesis

The synthetic sample uses **$12,500 fixed / 10 business days** for migration reconciliation, interface regression evidence, and a cutover replay packet. That is a commercial hypothesis only; no buyer or prime has accepted it.

## Source note

The package stores only public opportunity metadata and owner-supplied hashes/references. It does not redistribute the solicitation or vendor worksheets. A real pursuit should bind the exact retained solicitation/addendum bytes before relying on the packet.
