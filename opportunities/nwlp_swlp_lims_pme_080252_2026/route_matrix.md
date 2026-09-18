# Route matrix

The carrier evaluates three commercial postures. None is currently READY because the controlling buyer questionnaire is missing.

## `PRIME_LIMS`

Use only if the organisation can prove all of:

- a clinical pathology LIMS product that covers the buyer's required disciplines;
- comparable NHS/pathology-scale delivery;
- clinical-safety case/process;
- buyer-required regulatory/pathology compliance evidence;
- EPR and national-system integration capability;
- migration at scale with reconciliation/cutover controls;
- implementation, training and support capability;
- commercial delivery capacity for the future programme.

**Current posture:** `HOLD`. Do not present Commons/AquaTrace as a clinical pathology LIMS prime merely because they contain laboratory/data workflow software.

## `TEAMING_INTEGRATION_SPECIALIST`

Bounded subcontract/partner seam for a qualified prime. Required evidence gates:

- integration engineering;
- migration reconciliation;
- interface test harnesses;
- security/data governance;
- deterministic acceptance.

Prime keeps product, clinical/regulatory, NHS references, programme delivery and commercial authority. The carrier also requires `partner_prime_confirmed=true` before owner-review readiness.

## `TEAMING_VALIDATION_EVIDENCE`

Narrowest credible specialist posture. Required evidence gates:

- deterministic acceptance;
- migration reconciliation;
- data-lineage evidence;
- interface test harnesses;
- human release controls.

Possible work products after buyer/prime agreement: synthetic interface fixtures, migration reconciliation receipts, replay/idempotency tests, change/version evidence, acceptance manifests and operator-controlled release gates. This is not clinical validation and must not be described as such without the required clinical authority/evidence.

## `HOLD`

Use whenever the questionnaire is absent/stale, evidence is missing, a teaming prime is unconfirmed, or a mandatory buyer gate cannot be proven. HOLD is a correct commercial output, not a failure of the engine.
