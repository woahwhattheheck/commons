# 3-minute demo runbook

## 0:00–0:30 — problem

Show the synthetic input and explain the distinction between *doing* a task and the hidden work of anticipating, planning, deciding, and monitoring it.

Narration:

> A task list usually shows who bought the groceries. It often misses who noticed the pantry was low, planned the week, checked preferences, wrote the list, and remembered the timing. LoadLight makes those cognitive stages visible.

## 0:30–1:10 — local AI classification

Open `loadlight/model.py` and one unlabeled synthetic item. Run:

```bash
python -m loadlight.cli --input fixtures/demo.json --output-dir /tmp/loadlight-demo
```

Explain that unlabeled stage/domain fields are classified locally and human labels override the model.

## 1:10–2:05 — dashboard

Open `/tmp/loadlight-demo/dashboard.html`.

Show:

- cognitive-work share by actor;
- execution work separately;
- one multi-stage task concentrated with one actor;
- the stage-level handoff suggestion.

Say explicitly:

> This is not a fairness verdict. It is a visibility and coordination tool. The household decides whether the suggestion is appropriate.

## 2:05–2:35 — privacy and failure boundaries

Show the machine-readable report. Demonstrate that raw source text is absent and only the source SHA-256 is retained.

Mention fail-closed validation for duplicate IDs, unknown actors, unknown fields, invalid stage/domain labels, and naive timestamps.

## 2:35–3:00 — product path

Close with the intended product:

- local-first phone/desktop experience;
- opt-in imports from family calendars/messages;
- on-device extraction + confirmation;
- explicit handoff request/accept flow;
- aggregate trends without mental-health or relationship scoring.

Do not claim real-user validation, competition registration, submission, or award.
