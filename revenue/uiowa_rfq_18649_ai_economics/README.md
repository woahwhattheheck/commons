# AI workflow economics — UIOWA-078

Owner of this implementation: ZZ-ORBIT-27 / GPT-6 Astra Pro.
Operation: `uiowa-078-orbit27-20260919`.

This isolated preparation kit compares a task-equivalent non-AI baseline with an assisted workflow. All supplied examples are fictional and are not University findings, market prices, expected returns or purchasing recommendations.

## Model contract

Let N be monthly tasks multiplied by the adopted share. Assisted active effort includes preparation/generation handling, mandatory checking and expected incremental rework. Rework probability times rework minutes is incremental to the handling/checking already counted. Full manual fallback belongs in rework minutes when applicable; do not also add that fallback as a separate baseline cost.

Gross released hours = N × (baseline minutes − assisted handling minutes − checking minutes − rework probability × incremental rework minutes) / 60.

Positive released hours are multiplied by the explicitly stated capacity-realization fraction and labor-value rate. Negative released hours incur their full labor-value cost; poor outcomes are not discounted. New support and maintenance hours incur their full labor-value cost independently of the realization fraction.

Monthly net value = realized capacity value − support/maintenance labor value − all-in generation cost − recurring cash costs.

Upfront value cost = integration/training labor value + one-time cash costs. Horizon net value = horizon months × monthly net value − upfront value cost. Cash outlay is reported separately; released staff time is not automatically cash savings.

Inputs carry low/base/high assumptions, units and measurement needs. Missing values stay unknown. Box bounds describe independent assumption ranges, not probabilities or confidence intervals. Sensitivity and break-even thresholds identify which real measurements would change the discussion. Quality-equivalent completed outputs must be established before interpreting time differences.

## Planned runnable carrier

The completed carrier will contain a standard-library Python calculator, explicit input schema, positive/negative/indeterminate synthetic scenarios, a missing-input case, deterministic JSON/CSV/Markdown reports, formula-driven worksheet, operator guidance and regression tests. No live service calls, credentials, purchases, outreach or scheduling are part of this tool.
