# Revenue proof settlement ledger

`revenue_proof_ledger` is a deterministic, read-only reducer for receipts that
already exist. It does not query Slack, GitHub, payment providers, customers, or
banking systems and it cannot initiate a payment. Its purpose is to keep four
money states separate:

- **pipeline_expected** — canonical advertised/contracted opportunity amount;
- **earned_unsettled** — accepted current delivery value not yet backed by
  complete settlement evidence;
- **cash_settled** — net settled payment authorized only by complete evidence;
- **reversed_or_disputed** — settled refunds/reversals/disputes that back cash
  out without deleting delivery history.

Operation: `REVENUE-PROOF-SETTLEMENT-LEDGER-20260913`.

## Input

The input schema is `commons-revenue-proof-input/v1` with one `receipts` array.
Every receipt carries:

- `kind`: `opportunity`, `delivery`, `settlement`, or `lookup`;
- canonical `opportunity_id`;
- `source` reader/receipt identity;
- `authority`: `complete`, `partial`, or `unknown`;
- immutable lowercase `sha256:<64 hex>` `evidence_digest`.

Unknown fields are rejected. Money is accepted only as plain non-negative
decimal **strings**; binary floats are never used.

### Opportunity receipt

```json
{
  "kind": "opportunity",
  "opportunity_id": "github:acme/widget#42",
  "source": "github:issue",
  "authority": "complete",
  "evidence_digest": "sha256:...",
  "identity_status": "canonical",
  "currency": "USD",
  "expected_amount": "500.00"
}
```

Multiple Slack/GitHub/market receipts with the same canonical opportunity ID
are deduplicated. Currency or amount disagreement, or
`identity_status="ambiguous"`, makes the opportunity authority `unknown`.

### Delivery receipt

An accepted delivery supplies `delivery_id`, `state="accepted"`, `current`,
`currency`, and `earned_amount`. `credit` keeps `source_authors`, `reviewers`,
and `mergers` as separate lineages; later review/merge evidence cannot remint
source authorship. Multiple current accepted deliveries are ambiguous.

### Settlement receipt

A settlement has a globally unique `settlement_id`, `delivery_id`, `movement`
(`payment`, `refund`, `reversal`, or `dispute`), provider `state` (`settled`,
`pending`, `failed`), currency, and amount. Identical cross-source copies of the
same settlement ID count once. Reusing one settlement ID for different semantic
facts makes the affected opportunity unknown and authorizes zero settled cash.
Only `state="settled"` changes observed cash.

### Lookup receipt

A `lookup` receipt explicitly states whether the reader had complete evidence
for `scope="delivery"` or `scope="settlement"`. This is important: **absence of
a payment row is not proof of no payment.** Missing/partial/unknown lookup
authority cannot mint `cash_settled`.

## Fail-closed rules

The ledger authorizes settled cash only when the opportunity has one current
accepted delivery, canonical terms agree, delivery and settlement lookups are
complete, all relevant receipt authorities are complete, settlement IDs are
consistent, currency/amount arithmetic is coherent, and every counted
settlement points at the current delivery. Superseded delivery heads,
provider/read incompleteness, identity ambiguity, duplicate-ID conflicts,
overpayment, refund-underflow, or semantic mismatch produce `authority=unknown`
and `cash_settled=0` for that opportunity while retaining evidence and delivery
history.

Partial multi-payment arithmetic is exact. Settled refunds/reversals/disputes
subtract from net cash and increase the remaining earned-unsettled amount; they
do not erase authorship or acceptance history.

## CLI

```sh
python -m tools.revenue_proof_ledger.ledger receipts.json \
  --json-out revenue-ledger.json \
  --summary-out revenue-ledger.md
```

Both outputs are create-exclusive. The JSON includes a deterministic
`ledger_digest` over its canonical content. Exit status is `0` only when the
resulting ledger authority is `complete`; partial/unknown authority or any I/O
/input failure returns `2`.

## Verification

```sh
python -m unittest -v tools.revenue_proof_ledger.test_ledger
python -m py_compile \
  tools/revenue_proof_ledger/ledger.py \
  tools/revenue_proof_ledger/test_ledger.py
```

The focused suite covers cross-source opportunity dedupe, accepted-without-
payment, identical settlement dedupe, partial/multi-payment arithmetic,
refund/reversal accounting, incomplete lookup zero-mint behavior, source-credit
lineage, reused settlement IDs, superseded delivery settlements, ambiguous
opportunity identity, amount mismatch, input permutation determinism, content
hash binding, unknown-field rejection, and create-exclusive output behavior.
