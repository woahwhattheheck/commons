# ARM26BX06-NV012 Phase I evidence skeleton

Status: **internal owner-review artifact only**. It is not a proposal submission, certification, price commitment, or representation of eligibility.

## Technical thesis

A decision should be a versioned, machine-verifiable program rather than a prose snapshot. Every generation carries explicit objectives, options, constraints, assumptions, risks, bias checks, evidence identities, deterministic evaluation output, sensitivity information, and an unavoidable human-decision boundary.

The included kernel demonstrates three mechanics the Army topic asks to see:

1. **Formal decision objects.** Objectives, options, constraints, assumptions, risks, bias checks and evidence are strict schema elements instead of latent prompt context.
2. **Reproducible agentic evaluation.** Integer-only scoring, explicit constraints, canonical JSON, SHA-256 generation identity and deterministic tie-breaking make repeated runs reproducible.
3. **Refreshable decision programs.** Later generations bind the exact prior digest and expose evidence changes; every refresh requires new human review rather than inheriting stale authority.

## Demonstration 1 — point trade study

`examples/point_trade.json` is a synthetic commercial utility-vehicle battery chemistry decision. It exercises weighted objectives, hard constraints, provenance, risks, assumptions, bias checks, deterministic ranking and a computed runner-up swing threshold. It is deliberately non-operational and contains no government data.

## Demonstration 2 — long-horizon refresh

`examples/long_horizon_g1.json` and `examples/long_horizon_g2.json` form a synthetic commercial fleet telemetry procurement decision program. Generation 2 cryptographically binds generation 1 and changes evidence/assumptions so the evaluator moves to HOLD and requires human re-review.

## Governing boundaries

The software may emit a `machine_preference`; it never emits a final decision. High/critical risk, unresolved assumptions, failed/not-run bias checks, or no eligible option force `HOLD`. There is no provider integration, external contact, proposal submission, signature, spending or government-system mutation in this carrier.

## Phase I work-package outline

- **WP1 — Decision schema and evidence custody:** stabilize schema, provenance, generation identity and requirement mapping.
- **WP2 — Governed agentic workflow:** structured elicitation into schema, bounded planning, reproducible evaluator calls, and transparent tool/evidence receipts.
- **WP3 — Point-trade demonstration:** execute and measure a bounded single-generation study.
- **WP4 — Long-horizon decision program:** execute refresh cycles, generation changes and sensitivity analysis.
- **WP5 — Human-control and robustness evaluation:** hostiles for stale evidence, aliasing, malformed input, authority replay, unresolved risk and bias states.
- **WP6 — Transition/commercialization evidence:** map demonstrated mechanics to commercial engineering/acquisition use without inventing customer adoption.

## Submission blockers that stay HOLD until independently evidenced

- controlling DSIP solicitation/package bytes and exact deadline mechanics;
- small-business eligibility and ownership/control requirements;
- SAM/UEI and DSIP account readiness;
- any required registrations, certifications, representations or attachments;
- price/cost proposal authority;
- owner authorization to submit.

`qualification_gate.py` is intentionally fail-closed on those facts and can never authorize an external mutation.
