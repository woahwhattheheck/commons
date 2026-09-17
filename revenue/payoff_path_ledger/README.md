# Payoff-path ledger

This package makes one internal operating rule deterministic: **uncompensated work needs a retained payoff/conversion path, or a bounded strategic exception**.

It classifies exact work generations across bug bounties, competition prizes, paid discovery, partner workshare, product conversion, already-paid work, and strategic-unpaid work. `AMOUNT_UNKNOWN` is explicit and is never treated as zero.

## External evidence trust root

External term/outcome evidence is not trusted because a packet labels itself a bounty, paid work, or settled. Every `term_evidence` and `outcome_evidence` row carries an `auth_tag_hex`: HMAC-SHA256 over the complete normalized row (including exact work ID/generation, source ID/SHA, class/kind, observation/currentness, and economics) under the **host-retained** `PAYOFF_PATH_EVIDENCE_AUTHORITY_KEY_HEX` capability. The 32-byte lowercase-hex key is read only from the host environment; it is never accepted from packet/API/CLI arguments and is never emitted. A relabel, source remint, work transplant, outcome change, or economics mutation invalidates the tag. Receipts retain only SHA-256 of the active authority key so key-generation changes are visible without exposing the key.

The compiler intentionally does **not** include a signing command. An evidence authority must authenticate source facts outside the packet-ingest path, then issue the tag. Without the host capability, any packet containing external term/outcome evidence fails closed. Bounded `STRATEGIC_UNPAID` and plan-only `PRODUCT_CONVERSION` packets need no external-evidence key because they do not claim external compensation/outcome facts.

`PRODUCT_CONVERSION` without authenticated cash terms and every `STRATEGIC_UNPAID` lane require a nonempty conversion milestone, a strictly positive effort ceiling, and an expiry/review boundary. The compiler validates retained structure/provenance; it **does not establish that a milestone is realistic, likely, externally accepted, or economically attractive**.

Settled outcome for the exact work generation dominates attractive payoff evidence. An active duplicate/custody conflict also blocks a positive state. Current verification re-evaluates expiry/staleness against a process-clock capability captured when the module API is built; assigning a later module `_NOW` name cannot rewind current verification.

Positive states are internal policy states only. Authority is emitted from source-literal exact-false booleans and verified with exact bool type identity; it does not authorize contact, Muse election/consume, acceptance of terms, contract/signature, bounty/competition submission, invoice/receivable creation, payment/funds movement, cash or revenue claims, tax/accounting conclusions, or provider/account mutation. The implementation performs no network I/O.

## CLI

```bash
python -m revenue.payoff_path_ledger compile packet.json --out receipt.json
python -m revenue.payoff_path_ledger verify-integrity packet.json receipt.json
python -m revenue.payoff_path_ledger verify-current packet.json receipt.json
```

`compile` uses create-exclusive output and refuses to overwrite an existing file. `example.json` demonstrates the no-external-evidence bounded strategic path and therefore runs without the host HMAC capability.
