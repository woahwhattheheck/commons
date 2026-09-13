# Evidence-bound commercial funnel

`revenue/commercial_funnel` turns immutable commercial evidence references into a deterministic, buyer-neutral funnel packet across Commons' four first-class offering families: **PRODUCT**, **SERVICE**, **EXPERTISE**, and **DATA**.

It exists to enforce a simple commercial truth: **traffic, reply, acceptance, delivery, transfer, and cash are different facts**. One never silently promotes to another.

## Authority ceiling

The strongest successful state is `FUNNEL_PACKET_READY_FOR_HUMAN_REVIEW`. A packet is analytics, not commercial authority. Every generated packet and receipt states `false` for buyer-contact, acceptance, contract execution, fulfillment, transfer, provider/payment mutation, cash-availability, accounting/tax, and revenue-recognition authority.

This package performs no network requests and no external mutations. Evidence references are immutable Git commit + path + SHA-256 bindings supplied by the caller. The compiler validates their shape and cross-event use; **it does not claim that a remote provider was queried or that the referenced bytes are authentic merely because a caller supplied a hash**. Provider/source capture remains a separate evidence-producing step.

## Stages

Normal stages are strictly ordered:

`TRAFFIC -> REPLY -> ACCEPTANCE -> DELIVERY -> TRANSFER -> CASH`

Special events are tracked without promotion:

- `NONCASH_AWARD`: records an exact integer quantity of a named non-cash asset. It never enters cash totals.
- `CASH_REVERSAL`: binds a prior `CASH` event ID and exact currency/minor-unit amount. Refunds/chargebacks/reversals reduce net-cash analytics and cannot exceed the referenced cash event.

A stronger immutable event may include `proves` for prior stages when that one evidence artifact genuinely establishes them. `proves` can only point backward; it cannot invent a future stage.

## Fail-closed rules

The compiler rejects malformed schemas, duplicate opportunity IDs, floats, non-UTC timestamps, mutable/short commit refs, traversal paths, non-integer money, and secret/PII-shaped values. Opportunity analytics HOLD on event-ID conflicts, future/stale evidence, stage gaps, impossible stage time order, cross-opportunity evidence reuse, orphan/mismatched/excess reversals, and related evidence conflicts.

Duplicate replay of an **identical** event is idempotent. Input opportunity/event order does not change output bytes or receipt identity.

Evidence older than 366 days is HOLD for this current-funnel packet. Archive older cohorts separately rather than weakening the current evidence window.

## Deterministic outputs

`compile` writes, create-exclusively:

- `report.json` — canonical analytics body before self-describing output hashes;
- `report.csv` — one deterministic opportunity row per ID;
- `report.md` — human review summary;
- `packet.json` — canonical packet including output hashes;
- `receipt.json` — content-addressed receipt binding semantic input, packet, outputs, evaluation time, and the authority ceiling.

The CLI refuses to overwrite any of those files or follow a symlink at the output path.

## CLI

From repository root:

```bash
python -m revenue.commercial_funnel.cli compile \
  revenue/commercial_funnel/example_input.json \
  --as-of 2026-09-13T10:10:00Z \
  --out-dir /tmp/commercial-funnel-example

python -m revenue.commercial_funnel.cli verify \
  revenue/commercial_funnel/example_input.json \
  --as-of 2026-09-13T10:10:00Z \
  --packet /tmp/commercial-funnel-example/packet.json \
  --receipt /tmp/commercial-funnel-example/receipt.json \
  --report-json /tmp/commercial-funnel-example/report.json \
  --report-csv /tmp/commercial-funnel-example/report.csv \
  --report-md /tmp/commercial-funnel-example/report.md
```

Exit codes: `0` ready/verified, `2` malformed/refused I/O contract, `3` compiled packet contains HOLD opportunities, `4` verification mismatch.

## Money and conversion metrics

Cash is exact integer minor units and remains grouped by currency. There is no implicit FX conversion. Funnel counts and dropoffs include only opportunities whose evidence set is not HOLD, preventing malformed/stale/conflicted evidence from inflating conversion rates. Held opportunities remain visible with explicit reasons and next action `REVIEW_HOLD_REASONS`.

## Development gate

```bash
python -m py_compile revenue/commercial_funnel/*.py
python -m unittest -v revenue.commercial_funnel.test_ledger
python -O -m unittest -v revenue.commercial_funnel.test_ledger
```

The focused suite includes a 128-opportunity deterministic acceptance corpus plus hostile replay, stage-skip, stale/future, evidence-reuse, reversal, type, timestamp, source-ref, output-order, PII/secret, and receipt-tamper cases.
