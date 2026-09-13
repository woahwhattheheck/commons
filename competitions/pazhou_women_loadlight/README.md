# LoadLight

**Make invisible planning work visible — then make it handoffable.**

LoadLight is a privacy-first AI prototype for the **Women-Friendly AI Product** track of the 5th Pazhou Algorithm Competition. It focuses on cognitive household labor: anticipating needs, planning, deciding, following up, and monitoring — work that conventional task lists often record only after someone has already done the thinking.

The prototype combines a tiny local text classifier with a deterministic workload engine. It can classify unlabeled coordination items, measure where cognitive stages are concentrated, and generate explicit stage-level handoff suggestions. It does **not** diagnose mental health, score relationship quality, make safety/medical decisions, or label a household “fair” or “unfair.”

## Why this problem

Recent research and official time-use data point in the same direction:

- OECD reports women average about **4 hours/day** of unpaid care and domestic work versus about **2 hours/day** for men across OECD countries.
- Aviv et al. (2025), in a sample of 322 mothers of young children, found mothers reported **72.57% of cognitive household labor** and 63.64% of physical domestic labor.
- U.S. BLS 2025 time-use data report women averaging **2.4 hours/day** in household activities versus **1.6 hours/day** for men.

LoadLight does not assume every household has the same pattern. It measures the pattern in the supplied coordination record and makes the hidden stages explicit.

## Run it

```bash
python -m loadlight.cli \
  --input fixtures/demo.json \
  --output-dir /tmp/loadlight-demo
```

Outputs:

- `/tmp/loadlight-demo/report.json` — deterministic machine-readable report;
- `/tmp/loadlight-demo/dashboard.html` — static no-server dashboard.

The report omits raw source text and stores SHA-256 source-text digests instead. Those digests support integrity/deduplication; they are not a substitute for encryption or anonymization of guessable short text.

## Test it

```bash
python -m py_compile loadlight/*.py tests/*.py submission/check_packet.py
PYTHONPATH=. python -m unittest -v
PYTHONPATH=. python -O -m unittest -v
python submission/check_packet.py
```

## Product behavior

Input uses `loadlight-intake/v1`:

```json
{
  "schema": "loadlight-intake/v1",
  "household_id": "synthetic-household-001",
  "actors": ["Alex", "Jordan"],
  "items": [
    {
      "id": "1",
      "task": "school field trip",
      "text": "Follow up because the school has not confirmed",
      "actor": "Alex",
      "effort_minutes": 10
    }
  ]
}
```

If `stage` or `domain` is absent, a small local multinomial Naive Bayes model supplies a prediction. Human labels, when present, always win. The deterministic layer then:

1. weights cognitive stages separately from execution;
2. computes each actor's visible cognitive-work share;
3. detects a task where multiple cognitive stages are concentrated with one actor;
4. suggests one explicit stage that could be handed off to a lower-loaded actor;
5. leaves the actual assignment decision to the household.

## Privacy and authority boundary

- raw source text is excluded from the output report/dashboard;
- no partner surveillance or hidden-data ingestion;
- no mood, diagnosis, stress, depression, relationship-quality, abuse, or safety inference;
- no automatic task reassignment;
- no moral fairness score;
- no external messages, purchases, calendar mutations, or provider actions;
- no competition registration/submission/award claim.

The current repository evidence is a **synthetic prototype**. It is not real-user validation.

## Competition packet

- [Business plan](docs/business-plan.md)
- [Chinese executive summary](docs/executive-summary-zh.md)
- [Architecture](docs/architecture.md)
- [Research basis](docs/research-basis.md)
- [3-minute demo runbook](docs/demo-runbook.md)
- [Submission state](submission/manifest.json)

The official women-friendly product track accepts teams of up to five with no female-member minimum for this subtrack. Registration closes September 15, 2026. Portal registration, team identity, terms acceptance, and final upload remain authenticated human actions and are intentionally marked pending.
