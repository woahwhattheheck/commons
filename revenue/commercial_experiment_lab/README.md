# Evidence-bound commercial experiment lab

`revenue/commercial_experiment_lab` answers a different question from the commercial funnel:

> Given a **predeclared cohort and arm assignment**, which segment × offer × proof-package × route arm is associated with stronger evidenced outcomes?

It does not send outreach, discover leads, mutate a CRM, or decide that an account may be contacted. It compiles the real `revenue/commercial_funnel` input first and uses that package's normalized opportunity outcomes as the only source of REPLY / ACCEPTANCE / CASH truth.

## Why this exists

Commons already distinguishes traffic, reply, acceptance, delivery, transfer and cash. That prevents false promotion of weak evidence. The experiment lab adds the missing strategy layer: a frozen experiment plan, frozen opportunity-to-arm assignments, deterministic descriptive metrics, and a next-wave **review recommendation**.

Message count is never a success metric here. An arm can only improve its commercial outcome metrics when the upstream funnel has evidence for stronger stages.

## Frozen plan and assignment model

Input schema: `commons-commercial-experiment-input/v1`.

A plan declares:

- stable `id` and `revision`;
- one offering `family`;
- immutable plan source reference and UTC `declared_at`;
- the complete opportunity-ID cohort;
- 2–32 arms;
- per-arm `segment`, exact upstream `offer_id` + `offer_version`, `proof_package`, and `route_class`;
- a minimum eligible sample per arm;
- predeclared integer-basis-point thresholds for expand / pause review.

Assignments bind each frozen opportunity exactly once to one arm. Every assignment must:

1. occur at or after plan declaration;
2. occur before the opportunity's **first upstream funnel event**;
3. bind an exact immutable evidence reference;
4. match the upstream opportunity family and exact offer identity.

A missing assignment, duplicate/cross-arm opportunity assignment, post-outcome assignment, family mismatch, or offer rewrite is a hard refusal.

The lab validates immutable-reference **shape** offline. It does not independently authenticate Git hosting, commit time, or remote bytes, and explicitly reports `source_authenticity_asserted_by_lab: false`. Provider/source capture belongs upstream.

## Outputs

A successful compile creates, exclusively:

- `report.json` — deterministic analytical body;
- `report.csv` — one row per arm;
- `report.md` — human review summary;
- `packet.json` — report body plus output hashes;
- `receipt.json` — content-addressed receipt binding experiment identity, upstream funnel identity, packet and outputs.

Input identity is order-independent: it binds the normalized frozen plan + normalized assignments + the upstream funnel semantic `input_sha256`, not arbitrary JSON list order.

## Metrics

Only upstream opportunities whose state is `FUNNEL_PACKET_READY_FOR_HUMAN_REVIEW` enter performance rates or cash totals. Held opportunities remain visible and block an arm from an expand recommendation.

Per arm:

- assigned / eligible / held counts;
- cumulative stage counts;
- cumulative stage reach in exact integer basis points;
- adjacent stage transition rates in basis points;
- lower-median integer seconds from TRAFFIC to REPLY / ACCEPTANCE / CASH;
- gross, reversal and net cash by currency with **no implicit FX conversion**;
- deterministic recommendation and exact reasons.

Pairwise arm deltas are always labelled `OBSERVATIONAL_NOT_CAUSAL`.

## Recommendation states

Recommendations are deterministic applications of the plan's predeclared thresholds:

- `INSUFFICIENT_EVIDENCE` — minimum sample missing or any upstream HOLD is present in the arm;
- `PAUSE_REVIEW` — eligible sample is sufficient but reply reach is below the predeclared pause threshold;
- `EXPAND_CANDIDATE` — eligible sample is sufficient and both reply + acceptance reach meet their predeclared expand thresholds;
- `KEEP_TESTING` — sufficient clean sample exists but neither stop rule fires.

`EXPAND_CANDIDATE` means **candidate for human strategy review**, not permission to contact more buyers.

## CLI

Compile with trusted process UTC (there is intentionally no caller-selected production `--as-of`):

```bash
python -m revenue.commercial_experiment_lab.cli compile \
  revenue/commercial_experiment_lab/example_input.json \
  --out-dir /tmp/commercial-experiment-lab
```

Byte-verify the recorded historical compilation:

```bash
python -m revenue.commercial_experiment_lab.cli verify \
  revenue/commercial_experiment_lab/example_input.json \
  --packet /tmp/commercial-experiment-lab/packet.json \
  --receipt /tmp/commercial-experiment-lab/receipt.json \
  --report-json /tmp/commercial-experiment-lab/report.json \
  --report-csv /tmp/commercial-experiment-lab/report.csv \
  --report-md /tmp/commercial-experiment-lab/report.md
```

Exit codes: `0` success, `2` malformed/refused I/O/input, `4` verification mismatch.

Library callers may pass an explicit `as_of` to `compile_experiment` for deterministic historical replay/tests. Production CLI compilation always uses process UTC.

## Authority ceiling

Every packet and receipt explicitly sets all of these to `false`: buyer contact, send/resend, mailbox/CRM/provider mutation, calendar booking, proposal/bid submission, contract/signature, pricing commitment, payment request/collection, bank/wallet action, fulfillment, cash-availability assertion, accounting/tax authority, and revenue recognition.

Existing DNR, suppression, consent, collision, provider and owner controls remain authoritative.

## Development gate

```bash
python -m py_compile revenue/commercial_experiment_lab/*.py
python -m unittest -v revenue.commercial_experiment_lab.test_compiler revenue.commercial_experiment_lab.test_cli
python -O -m unittest -v revenue.commercial_experiment_lab.test_compiler revenue.commercial_experiment_lab.test_cli
```

The repository checkout additionally runs an integration test through the real `revenue.commercial_funnel` compiler.
