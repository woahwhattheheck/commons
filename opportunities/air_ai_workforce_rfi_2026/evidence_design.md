# Evidence-design appendix

## Theory of change

**Input:** a workforce partner already delivering career-navigation/readiness services; a bounded AI support layer; staff training; participant consent/governance; AIR evaluation design.

**Mechanism:** AI reduces search/drafting/synthesis burden and creates structured, revisable next-step support; staff supervision prevents consequential autonomous decisions; provenance/version logging makes failure and drift measurable.

**Near-term outcomes:** time to complete bounded tasks; task-quality rubric; factual/support error rate; staff accept/revise/reject rate; staff handling time; participant-reported usefulness/trust; escalation/rework.

**Downstream outcomes only when already lawfully measured:** training progression/completion, verified referral completion, placement, time-to-placement, retention, and wage progression. Do not add collection merely because a metric is interesting.

## Comparison options

Choose before launch with AIR and the delivery partner:

1. **Cluster or individual randomized encouragement / service variant**, where operationally and ethically feasible.
2. **Stepped-wedge rollout** across sites/cohorts when universal eventual access is desirable.
3. **Matched contemporaneous comparison** using pre-specified covariates when randomization is infeasible.
4. **Interrupted time series / difference-in-differences** only when pre-period quality and parallel-trend assumptions are credible.

Never select the design after seeing favorable outcomes.

## Instrumentation contract

For each evaluated interaction, retain only what the pre-specified analysis needs:

- opaque participant/session ID;
- service/task type;
- canonical event time;
- model/provider/model-version/configuration identity;
- prompt/template revision digest;
- evidence/source digests used by the system;
- response/output digest and structured failure flags;
- staff accept/revise/reject/escalate action;
- bounded latency/rework metrics;
- consent/governance version;
- evaluation cohort/assignment only when required by the design.

Direct names, email, phone, addresses, resumes, or other source documents should remain in the partner's governed system unless the evaluation explicitly requires transfer.

## Fairness and responsible-AI analysis

Pre-specify subgroup metrics and minimum sample/reporting rules. Evaluate at least:

- factual/support error rates;
- unsafe/inappropriate recommendation rates;
- staff override/escalation rates;
- task completion and quality;
- latency/rework;
- participant-reported usefulness/trust where collected.

A fairness dataset may need protected/demographic variables; if so, collect/use them under a separate lawful, consented evaluation protocol and do not expose them to generation by default.

## Worker voice

Worker voice is not a satisfaction checkbox. Include structured qualitative inquiry on usefulness, confusion, perceived pressure to use AI, accessibility, privacy expectations, and whether recommendations reflect actual constraints. Feed findings into bounded product changes with model/config revisions recorded.

## Evaluator independence

AIR should be able to:

- inspect the pre-specified outcome definitions and analysis plan;
- distinguish product telemetry from participant outcomes;
- audit model/configuration changes and missingness;
- reproduce core derived metrics from governed extracts;
- see negative cells and failures, not only averages;
- challenge causal language that exceeds the design.

## Failure modes to pre-register

- fabricated or stale resource/labor-market information;
- unsupported certainty;
- harmful or discriminatory guidance;
- sensitive-data leakage;
- model drift after update;
- staff automation bias;
- subgroup quality gaps;
- increased staff verification burden;
- participant disengagement or accessibility barriers;
- evaluator leakage / tuning to the metric;
- selective logging or missingness correlated with failure.

## Evidence-to-action cadence

Use a short operational learning loop (e.g. weekly/biweekly implementation review) for safety/quality signals and a separately governed evaluation cadence for outcome inference. Operational iteration must preserve intervention-version identity so evaluation does not pool materially different systems.
