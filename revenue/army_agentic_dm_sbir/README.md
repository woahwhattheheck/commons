# Army SBIR ARM26BX06-NV012 — readiness and prototype contract

Status: **TECHNICAL_BUILD_OK / ADMIN_READINESS_HOLD**

Owner lane: `ARMY-SBIR-AGENTIC-DM-ARM26BX06-NV012-SOLZ-20260914`

This carrier turns the Army's public Phase-I desired outcomes into a small, deterministic
prototype contract. It is not a proposal submission, eligibility attestation, cost proposal,
Army contact, award claim, or authorization to process controlled information.

## Controlling public sources

- Army topic: https://armysbir.army.mil/topics/agentic-ai-schema-driven-decision-management/
- Army SBIR/STTR eligibility and application requirements:
  https://armysbir.army.mil/howitworks/eligibility/
- Army program funding overview: https://armysbir.army.mil/howitworks/
- Army Phase schedule/funding page: https://armysbir.army.mil/phase/
- Army FAQ Phase-I page:
  https://armysbir.army.mil/faq/what-is-a-phase-i-contract-2/
- SAE reference identified by the Army topic:
  https://saemobilus.sae.org/papers/concept-execution-ai-agentic-decision-intelligence-framework-product-planning-concept-development-2025-01-0455

The exact topic identifies SBIR `ARM26BX06-NV012` and STTR `ARM26TX06-NV003`.
It asks for a schema-driven Decision Management foundation plus governed agentic AI,
with objectives/options/constraints/assumptions/risks/bias checks as first-class objects,
reproducible evaluation, clear "what flips the decision" logic, and two demonstrations
covering a point trade study and a long-horizon refreshable decision program.

### Funding truth boundary

The exact public topic page does not state a cost ceiling in the page content captured for
this carrier. Army program pages are not internally uniform: the current "How It Works"
page says Phase I can provide up to $300,000 for up to six months, while the current
phase/FAQ pages state Army SBIR Phase I awards up to $250,000. Therefore **this carrier
does not encode an exact topic budget ceiling**. The controlling Release-6/DSIP
instructions must be read before any cost proposal or submission-ready claim.

## Eligibility truth boundary

Army's public SBIR eligibility page requires, among other things, a U.S.-based for-profit
small business, 500 or fewer employees, qualifying ownership/control, and a principal
investigator whose primary employment is with the small business. It also requires the
relevant SAM and SBIR.gov registration path and proposal submission through the
Department submission system.

No authenticated registration evidence was verified while creating this carrier.
That absence is not proof that registration does not exist; it means this repository must
**not self-certify eligibility or submission readiness**. Administrative/entity/account
facts remain owner-controlled gates.

## Phase-I prototype contract

The agent is a proposal surface, not an authority surface.

A `DecisionEpisode` contains:

- objectives;
- assumptions with explicit acceptance state;
- risks with explicit disposition;
- bias checks with explicit pass state;
- evidence records with source, observation time, validity window, status, payload digest;
- weighted criteria bound to evidence identifiers;
- options with integer-basis-point criterion scores;
- generation number and as-of time.

`prototype.py` evaluates one exact generation and emits either:

- `HOLD`, with deterministic reasons; or
- `DECISION_READY`, with ranking, winner, runner-up, evidence-generation digest,
  mechanical flip thresholds, and a replay receipt digest.

Authority invariants:

1. Floats are forbidden in the authority-bearing schema; integer basis points avoid
   cross-runtime float serialization ambiguity.
2. Revoked, stale, future-dated, malformed, or digest-mismatched evidence fails closed.
3. Missing assumptions, risks, bias checks, criteria, evidence bindings, or option scores
   fails closed.
4. The evaluator never mutates the caller's decision program.
5. Post-evaluation mutation produces a different input and receipt digest; it cannot
   rewrite an earlier receipt.
6. Refresh creates a new generation. Historical generations remain independently
   replayable.
7. Agent prose cannot create `DECISION_READY`; only the deterministic typed evaluator can.
8. `what_flips` is machine-computed from the exact winner/runner-up margin and criterion
   weights rather than written as explanatory prose.

## Synthetic demonstrations

All fixtures are intentionally synthetic and non-sensitive. They are not Army data,
vehicle specifications, acquisition facts, CUI, export-controlled data, or buyer evidence.

### Demo A — point trade study

`demo_point_trade_study.json` models a synthetic ground-vehicle power/thermal architecture
choice using mass, thermal performance, and supplier lead-time criteria. It demonstrates
a single signer-ready ranking plus recomputable flip thresholds.

### Demo B — long-horizon decision refresh

`demo_refresh_generation_1.json` and `demo_refresh_generation_2.json` model a synthetic
vehicle-compute architecture decision at two evidence generations. Generation 2 carries
new synthetic cyber, compatibility, and availability evidence and can change the winner
without mutating Generation 1.

## Verification

Local source verification for the exact files in this carrier:

```text
python -m py_compile prototype.py test_prototype.py
python -m unittest -v test_prototype.py
```

Observed before publication:

```text
py_compile: PASS
unittest: 11/11 PASS
```

Hostiles cover canonicalization stability, stale evidence, revoked evidence, evidence
payload mutation without digest update, missing bias checks, missing scores,
post-evaluation mutation, deterministic replay, mechanical flip thresholds, forbidden
float authority, and generation-separated refresh.

Hosted CI is not claimed by this carrier unless a provider run is later observed.

## Competitive thesis

The Army topic itself points to an existing structured-decision/COTS baseline and to an
SAE agentic decision-intelligence reference. A proposal should therefore **not** claim
generic "LLM + decision science + workflow orchestration" as the differentiator.

The sharper technical wedge is:

- auditable decision programs as verifiable software artifacts;
- immutable evidence generations and deterministic replay;
- fail-closed evidence freshness and provenance;
- strict separation between agent proposal and decision authority;
- executable flip conditions;
- adversarial mutation/custody testing;
- refresh without historical rationale rewrite; and
- provider-neutral/open implementation posture suitable for later transition.

## Remaining gates

This carrier is intentionally incomplete. It becomes `READY_TO_SUBMIT` only when all
controlling evidence exists:

- exact Release-6/DSIP solicitation and current submission dates/cost limits captured;
- business/ownership/employee-count eligibility evidenced by an authorized owner;
- PI primary-employment eligibility evidenced;
- SAM and SBIR.gov/required submission-account registrations evidenced;
- any security/CMMC/foreign-risk representations resolved from controlling instructions;
- technical reuse map bound to actual Commons paths/blobs/commits;
- demo outputs and proposal claims backed by reproducible receipts;
- Phase-I work plan, cost, staffing, commercialization and transition plan completed;
- no conflicting owner/submission lane exists.

Until then: **build technical evidence, do not submit or self-certify**.
