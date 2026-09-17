# Payoff-path ledger

This package makes one internal operating rule deterministic: **uncompensated work needs a retained payoff/conversion path, or a bounded strategic exception**.

It classifies exact work generations across bug bounties, competition prizes, paid discovery, partner workshare, product conversion, already-paid work, and strategic-unpaid work. Evidence is scoped to `subject_work_id` plus its exact generation SHA-256. Generic project/issue prose cannot authenticate compensation terms. `AMOUNT_UNKNOWN` is explicit and is never treated as zero.

`PRODUCT_CONVERSION` without external cash terms and every `STRATEGIC_UNPAID` lane require a nonempty conversion milestone, a strictly positive effort ceiling, and an expiry/review boundary. The compiler validates the structure and retained provenance of that plan; it **does not establish that the milestone is realistic, likely, externally accepted, or economically attractive**.

Settled outcome for the exact work generation dominates attractive payoff evidence. An active duplicate/custody conflict also blocks a positive state. Current verification re-evaluates expiry/staleness against fresh process time after authenticating the historical receipt.

Positive states are internal policy states only. They do not authorize contact, Muse election/consume, acceptance of terms, contract/signature, bounty/competition submission, invoice/receivable creation, payment/funds movement, cash or revenue claims, tax/accounting conclusions, or provider/account mutation. The implementation performs no network I/O.

## CLI

```bash
python -m revenue.payoff_path_ledger compile packet.json --out receipt.json
python -m revenue.payoff_path_ledger verify-integrity packet.json receipt.json
python -m revenue.payoff_path_ledger verify-current packet.json receipt.json
```

`compile` uses create-exclusive output and refuses to overwrite an existing file.
