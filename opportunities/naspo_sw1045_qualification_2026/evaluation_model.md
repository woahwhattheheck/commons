# Evaluation-model status

## What is authoritative today

The official NASPO public page is authoritative for solicitation identity, open status, lead state, dates, cooperative purpose and broad public-sector reach.

It is **not** the complete evaluation plan.

## What mirrors currently suggest

Public mirror snapshots describe:

- Category 1 Consulting and Category 2 Services as independently evaluated;
- a staged evaluation process;
- an Attachment C titled `RFP Evaluation Plan`;
- an Attachment H titled `Requirements Response Table`.

These are useful discovery facts only. This package does not publish guessed weights, point totals, minimum thresholds, tie breakers, preference formulas or category carryover rules.

## What must be captured before effort allocation can be score-driven

From the official packet, bind:

1. every evaluation stage and pass/fail screen;
2. every scored criterion and weight/point maximum;
3. any interview/demo/BAFO/clarification stage;
4. category-specific minimum qualifications;
5. price evaluation method and units;
6. reference/past-performance scoring;
7. preference / reciprocal preference / responsibility rules;
8. award structure (single/multiple by category);
9. cure/waiver discretion, if any;
10. addenda that amend any of the above.

Each extracted requirement must carry:

- `requirement_id`;
- `category_id`;
- exact source document ID;
- exact source-document SHA-256;
- bounded paraphrase / requirement text.

Only then may `requirements.source_authority` become `CONTROLLING_PACKET` and `evaluation_model_status` become `EXACT_CAPTURED`.

## Effort rule before then

Spend effort on reusable specialist proof and partner qualification, not speculative proposal prose. The current technical seam has value across both categories; the buyer-facing response structure and score optimization remain blocked on exact source capture.
