# UIOWA-077 — Organizational AI adoption readiness

A runnable, offline assessment of **team-level** capability to adopt AI-assisted
ways of working, plus capability-development options mapped to **0–90 / 90–180 /
180+ day** horizons.

Built for work order **UIOWA-077** (seat `OP5-JUNIPER`). Python 3 standard
library only, no network, deterministic output.

---

## The problem this is designed around

A "team AI readiness" instrument is one bad design decision away from being a
performance-review tool, and one lazy default away from turning *"nobody gave us
the evidence"* into *"this team is behind."* Both failures are easy to make and
hard to walk back once a number is in a slide.

So the six rules below are enforced **in code**, each with a test that fails if
the rule is removed.

| # | Rule | Where it lives |
|---|---|---|
| 1 | **Organization, not individuals.** A record carrying an individual identity key is *rejected*, not quietly anonymised. | `scan_identity_keys`, `load_teams` |
| 2 | **Thin signal is not a low rating.** Below the contributor floor or the indicator floor → `UNKNOWN`, never `ABSENT`, never zero. | `resolve_dimension` |
| 3 | **`UNKNOWN` is excluded from every denominator.** Coverage is reported as plain counts. No composite score, maturity level, peer percentile, or certification claim exists anywhere in the output. | `coverage`, `BANNED_OUTPUT_KEYS` |
| 4 | **Recollection is not a record.** An indicator supported only by an interview statement cannot reach `ESTABLISHED`; it is downgraded to `EMERGING` and the reason is printed beside it. | `resolve_dimension` |
| 5 | **Every effort figure carries its own basis.** A staff-effort range is invalid without both `assumption_basis` and `validating_evidence`. | `validate_effort` |
| 6 | **You cannot plan to fix what you have not established is broken.** An `UNKNOWN` dimension produces an **evidence request**, never a development option. | `select_options`, `evidence_request` |

Rule 5 is carried over from this seat's original UIOWA-070 prep (that order was
already claimed). It is the same discipline: a planning number that does not say
what it assumes and what would confirm it is not a number, it is a decoration.

---

## Run it

```bash
cd revenue/uiowa_rfq_18649_adoption_readiness

# the worked assessment over the three synthetic teams
python3 readiness.py

# the interview instrument on its own
python3 readiness.py --instrument-only

# hostile inputs: rejected records, rejected observations
python3 readiness.py --teams fixtures/hostile_teams.json --outdir out_hostile

# hostile catalog: malformed options, phase inversion, dependency loop
python3 readiness.py --catalog fixtures/hostile_catalog.json --outdir out_badplan

# tests
python3 -m unittest -v test_readiness
```

Useful flags: `--min-contributors N` (default 3), `--min-indicators N` (default
2), `--teams / --indicators / --catalog / --outdir`.

### Outputs (written to `out/`)

| File | What it is |
|---|---|
| `interview_instrument.md` | The deliverable interview instrument — 6 dimensions, 15 indicators, each with what to ask, what to ask to *see*, and why it matters. |
| `readiness_report.md` | The worked assessment: per-team capability states with the evidence actually looked at, evidence requests, and the horizon plan. |
| `readiness_worksheet.csv` | One row per team × dimension: state, reason, indicators observed, evidence sources, downgrade notes. |
| `capability_options.csv` | One row per planned option: horizon, capability gained, effort range, `assumption_basis`, `validating_evidence`, dependencies, observable indicator. |
| `evidence_requests.csv` | What to go and get for every `UNKNOWN`, and what would validate it. |
| `readiness_assessment.json` | The whole structure, plus a `content_digest` so a second operator gets identical output or a loud difference. |

---

## What the worked example actually shows

Verbatim from `python3 readiness.py`:

```
teams assessed: 3   rejected records: 0   rejected options: 0
  T-ESS    contributors=7   state=5/6 unknown=1  established=2 emerging=2 absent=1  options=5  evidence_requests=1
  T-IAM    contributors=2   state=0/6 unknown=6  established=0 emerging=0 absent=0  options=0  evidence_requests=6
  T-RIS    contributors=5   state=5/6 unknown=1  established=1 emerging=3 absent=1  options=6  evidence_requests=1
diagnostics: 0 error(s); sequencing open questions: 3
content digest: 9a125e4e1bfca78387f5efa4ced28cb6932bba34bd957fc1e163ff3693790db2
```

**T-ESS — a real strength beside a real gap.** Practical training and available
support are `ESTABLISHED`, resting on a training roster, an onboarding checklist
and a queue routing rule whose owner is a role rather than a person. Capacity to
evaluate new approaches is `ABSENT`: no evaluation note in the change log, no
acceptance check, and nobody the team could name who is able to stop an approach
already in use. Workflow fit is `UNKNOWN` — no evidence was supplied — so it
yields an evidence request rather than a guess.

**T-RIS — recollection caught in the act.** Two indicators were offered as
`ESTABLISHED` on an interview statement alone: a well-used shared approach, and a
named person who can reverse an adopted decision. Neither produced an artifact
when asked. Both were downgraded, with the reason recorded:

```
- SHR-1: ESTABLISHED downgraded to EMERGING (recollection_only) - the only evidence is an interview statement, not a record.
- EVL-3: ESTABLISHED downgraded to EMERGING (recollection_only) - the only evidence is an interview statement, not a record.
```

**T-IAM — thin evidence, held open.** Two contributors, below the floor of three.
Its observations look confident, and the engine still refuses to read them as an
organizational state: `0/6` dimensions get a state, 6 evidence requests are
raised, and **zero** development options are produced. That `0/6` is the absence
of a reading, not a bad reading.

**Three sequencing open questions, not errors.** `OPT-SUP-02` depends on
`OPT-FIT-01`, which is not in T-ESS's plan because workflow fit is `UNKNOWN`
there. The tool neither drops the dependency nor assumes it is satisfied — it
says so and asks.

### Hostile runs

`fixtures/hostile_teams.json` → 4 records rejected: two for carrying individual
identity (`observations[0].employee_id`, a named `respondents` roster), two for a
contributor count that was the string `"several"` or simply absent. The fifth is
assessed with four unusable observations stripped (missing evidence source,
unknown indicator, invalid state, invalid evidence kind) — and every affected
dimension lands on `UNKNOWN`. **A rejected observation is absent evidence; it
never becomes an `ABSENT` finding.**

`fixtures/hostile_catalog.json` → 3 options refused entry (missing observable
indicator; missing `assumption_basis` and `validating_evidence`; attempting to
trigger off `UNKNOWN`), plus a detected `dependency_cycle`, a `phase_inversion`
(`OPT-X-EARLY` scheduled in 0–90 while depending on something that lands in
180+), and a `missing_prerequisite`.

---

## Tests

```
Ran 49 tests in 0.057s

OK
```

Hostile and missing-data cases are the substance of the suite, not an appendix:
an identity-bearing record, a boolean contributor count (`True` must not be read
as `1`), a team below the contributor floor, a dimension below the indicator
floor, a duplicate observation (rejected, never merged), an option missing its
basis, a phase inversion, a dependency loop, a dimension deleted out from under
the catalog, and an empty input file.

Three tests exist specifically to stop this becoming something it must not be:
`test_output_contains_no_scoring_or_certification_key`,
`test_no_individual_identity_key_reaches_the_output`, and
`test_unknown_never_produces_a_development_option`.

---

## What is real, what is draft

**Real and working:** the engine, the six enforced rules, the diagnostics, the
dependency and phase checks, the deterministic digest, the four exports, and the
test suite. Run it and it does what this file says.

**Draft content, not findings:** the 15 interview prompts and the 12
capability-development options are a *starting point* for operational interviews.
They are written to be argued with and replaced.

**Fiction, labelled as such:** all three teams, every evidence source, every
locator. `T-ESS`, `T-RIS` and `T-IAM` are invented to exercise the engine. Every
synthetic evidence source is prefixed `SYNTHETIC`. **Nothing in this directory is
a University team, a University record, a University finding, or a measured
University figure**, and the engine prints that on every report it generates.

**Effort ranges are planning placeholders.** Each one states what it assumes and
names the real data that would confirm or replace it. None is a measurement.

### University inputs still UNKNOWN

Nothing below has been supplied, and none of it is guessed at, defaulted, or
inferred anywhere in the code:

- Which teams or units are in scope, and their real contributor counts.
- Whether any written guidance on assistive tooling exists today, who owns it,
  and when it was last reviewed.
- Actual training records, onboarding materials, and whether an external trainer
  is required by local practice.
- Actual support routing and escalation for assisted-workflow questions.
- Whether written procedures exist for the workflows that would be mapped, and
  whether an exclusion needs sign-off outside the owning team.
- The real baseline for capability work: hours available per contributor per
  quarter, and what comparable internal guidance or training efforts have
  actually cost.
- Data-handling rules and their owners for each system in scope.
- Whether completed work with known-correct answers is retrievable, which is the
  precondition for `OPT-EVAL-02`.

Supply any of these and the corresponding `assumption_basis` should be replaced
by the measurement, not padded with it.

### Deliberately not in scope

No composite score, maturity level, peer percentile, benchmark position,
certification or compliance claim. No assessment of any individual. No live data,
no network access at runtime, no external service. No procurement or product
recommendation.
