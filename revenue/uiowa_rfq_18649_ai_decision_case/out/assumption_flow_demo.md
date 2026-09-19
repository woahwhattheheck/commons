# AI decision case — Drafting a service-change memo from an approved change ticket (SYNTHETIC)

**SYNTHETIC.** Every document, measurement, effort record and cost assumption below is invented for demonstration. Nothing here is a University of Iowa finding, measurement or price.

## Verdict

**BENEFICIAL** — assisted drafting costs less over the whole document lifecycle than the manual baseline, across the entire declared assumption range. [CASE-SYN-ESS-CHANGE-MEMO]

- the whole declared assumption range keeps net value above zero [CASE-SYN-ESS-CHANGE-MEMO]

## What the headline says

Producing a first draft took a mean of 6.0 minutes with assistance against 94.5 minutes authored manually — a 15.75x speed-up **on the drafting step alone**. [EVT-B-B1-1, EVT-B-B2-1, EVT-B-B3-1, EVT-B-B4-1, EVT-B-A1-1, EVT-B-A2-1, EVT-B-A3-1, EVT-B-A4-1]

That figure is true and it is not the basis for a decision. It measures the one step that got cheaper. [CASE-SYN-ESS-CHANGE-MEMO]

## What delivery actually costs

| | manual baseline | with assistance |
|---|---|---|
| mean minutes before acceptance | 120.8 | 39.0 | [DOC-B-B1, DOC-B-B2, DOC-B-B3, DOC-B-B4, DOC-B-A1, DOC-B-A2, DOC-B-A3, DOC-B-A4]
| mean minutes after acceptance | 3.0 | 2.5 | [DOC-B-B1, DOC-B-B2, DOC-B-B3, DOC-B-B4, DOC-B-A1, DOC-B-A2, DOC-B-A3, DOC-B-A4]
| mean minutes per delivered document | 123.8 | 41.5 | [DOC-B-B1, DOC-B-B2, DOC-B-B3, DOC-B-B4, DOC-B-A1, DOC-B-A2, DOC-B-A3, DOC-B-A4]
| observed range across documents | 118.0–128.0 | 39.0–48.0 | [DOC-B-B1, DOC-B-B2, DOC-B-B3, DOC-B-B4, DOC-B-A1, DOC-B-A2, DOC-B-A3, DOC-B-A4]

Per delivered document, assistance saves 82.2 minutes at the midpoint, with an observed range of 70.0 to 89.0 minutes saved. The range is the spread actually seen across the recorded documents, not an assumed tolerance. [DOC-B-B1, DOC-B-B2, DOC-B-B3, DOC-B-B4, DOC-B-A1, DOC-B-A2, DOC-B-A3, DOC-B-A4]

## Quality

Assisted drafts scored 0.896 mean completeness against 0.958 for manual drafts, over 4 and 4 measured documents. [QM-B-A1, QM-B-A2, QM-B-A3, QM-B-A4, QM-B-B1, QM-B-B2, QM-B-B3, QM-B-B4]

## Net value and the assumptions behind it

Over the declared horizon the net effect lies between 10,080 and 58,740 currency units. [ASM-B-001, ASM-B-002, ASM-B-003]

| assumption | value | declared range | basis |
|---|---|---|---|
| analyst_hourly_cost | 40.00 currency_per_hour | 40.00–110.00 | OVERRIDE | [ASM-B-001]
| documents_per_month | 24.00 documents_per_month | 18.00–30.00 | ASSUMED | [ASM-B-002]
| evaluation_horizon_months | 12.00 months | 12.00–12.00 | ASSUMED | [ASM-B-003]

These are stated assumptions, not measurements. Replacing any of them re-runs the case and re-renders this explanation. [ASM-B-001, ASM-B-002, ASM-B-003]

Explanation audit: PASSED — every quantity above cites a record in this case.

## What changed when the assumption moved

```
--- explanation (nominal)
+++ explanation (overridden)
@@ -34 +34 @@
-Over the declared horizon the net effect lies between 17,640 and 58,740 currency units. [ASM-B-001, ASM-B-002, ASM-B-003]
+Over the declared horizon the net effect lies between 10,080 and 58,740 currency units. [ASM-B-001, ASM-B-002, ASM-B-003]
@@ -38 +38 @@
-| analyst_hourly_cost | 85.00 currency_per_hour | 70.00–110.00 | ASSUMED | [ASM-B-001]
+| analyst_hourly_cost | 40.00 currency_per_hour | 40.00–110.00 | OVERRIDE | [ASM-B-001]
```
