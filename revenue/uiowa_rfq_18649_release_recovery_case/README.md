# UIOWA-109 — Integrated release-and-recovery case

Seat **OP5-UMBER** (Claude · Opus 5) · work order **UIOWA-109**, *"connect a release
problem to recovery evidence."*

Everything in this kit is **FICTIONAL**. `ess-prod`, `SVC-ESS`, `SVC-RIS`, `SVC-IAM`,
every digest, date and measurement were invented for artifact review. Nothing here
describes the University of Iowa, any real service, any real release, or any real
incident. No figure in this kit may be cited as a finding.

## What this is, and what it deliberately is not

The order's completion bar is *"each component's output agrees on the timeline and
source IDs; recovery claims follow actual synthetic verification records."*

That is **not** a request for another assessor. Three components already exist and
each is individually correct:

| Component | Lane | What it decides |
|---|---|---|
| Release provenance | `revenue/uiowa_rfq_18649_release_provenance` (UIOWA-057) | `deployments → artifacts → builds → sources` link/gap/contradiction |
| Recovery evidence | `revenue/uiowa_rfq_18649_recovery_evidence` (UIOWA-068) | backup → restore → dependency → business-function ladder |
| Environment view | *this kit* | where a release was verified vs. where it actually ran |

Three individually-correct components can still **disagree with each other**. The
provenance export can say the deployment happened at 22:00, the recovery export can
say the same deployment happened at 22:05, and both tools return green because
neither can see the other's clock. That disagreement is the real risk in a
multi-component delivery kit, and catching it is this kit's whole job.

So this adds **no new scoring model**. It holds one case — one shared event register
and one shared evidence register — projects it into each component's own contract,
and checks the projections against each other. It reuses 057's and 068's field names
rather than minting a fourth vocabulary.

### The design decision that makes disagreement detectable

Every moment in time is referenced through an **event reference**:

```json
{"event_id": "EVT-DEPLOY", "asserted_at": "2026-09-17T22:00:00Z"}
```

The authoritative timestamp lives **once**, in `events[].observed_at`. A component
reference may *also* carry `asserted_at` — what that component's own export claims.
A component that carries no clock of its own sets `asserted_at: null`, which is
honest and is not a finding.

If every component read its timestamp out of one shared field, agreement would be
structurally guaranteed and this checker would be theatre. It is not: the
disagreement has somewhere real to live, and `fixtures/timeline-disagreement.json`
puts it there.

## Run it

Python 3.9+, standard library only, no network at runtime. From this directory:

```sh
# the narrative case the order asks for
python3 release_recovery_case.py case.json --format markdown

# the clean control -- must return AGREED with zero findings, exit 0
python3 release_recovery_case.py fixtures/clean.json --format json

# one deliberately-broken fixture per defect class
python3 release_recovery_case.py fixtures/timeline-disagreement.json
python3 release_recovery_case.py fixtures/ordering-inversion.json --format csv

# every output at once
python3 release_recovery_case.py case.json \
  --json-output out/case_report.json \
  --csv-output out/agreement_matrix.csv \
  --markdown-output out/case_report.md \
  --emit-provenance out/projected_provenance_packet.json \
  --emit-recovery  out/projected_recovery_records.json \
  --emit-environment out/projected_environment_view.json

python3 release_recovery_case.py --schema     # the case contract
python3 make_fixtures.py                      # regenerate case.json + fixtures/
python3 -m unittest -v test_release_recovery_case.py
```

**Exit codes** mirror UIOWA-057 so the kits compose: `0` AGREED · `1` GAPS or
CONTRADICTIONS · `2` malformed input (diagnostic on stderr, **no report emitted**).

`AGREED` means the supplied records do not contradict each other. It is **not** a
release approval, a recovery certification, or a statement that the release was
safe.

## What it checks

| Check | Finding codes | Class |
|---|---|---|
| Components agree on when a shared event happened | `TIMELINE_DISAGREEMENT`, `REGISTER_UNKNOWN_BUT_ASSERTED` | contradiction / gap |
| Ordering constraints, scoped (see below) | `ORDERING_INVERSION` | contradiction |
| Every cited source and event id resolves | `UNRESOLVED_SOURCE_ID`, `UNRESOLVED_EVENT_ID` | gap |
| One identifier does not mean two things | `ID_COLLISION` | contradiction |
| Verified-where vs. ran-where; version/digest agreement | `ENVIRONMENT_DIFFERENCE`, `VERSION_DIFFERENCE`, `DIGEST_DIFFERENCE`, `NO_VERIFICATION_RECORD` | gap / contradiction |
| Provenance chain links | `BROKEN_CHAIN_LINK`, `MISSING_CHAIN_LINK`, `REVISION_DIFFERENCE`, `INPUT_COVERAGE_INCOMPLETE` | gap / contradiction |
| A recovery claim is carried by a real record | `UNSUPPORTED_RECOVERY_CLAIM`, `UNDECLARED_DEPENDENCY_RESULT`, `UNRESOLVED_DEPENDENCY` | gap |
| An event with no observed time stays UNKNOWN | `UNORDERABLE_EVENT` | gap |

A **contradiction** says two records cannot both be true (reconcile them). A **gap**
says evidence is absent (request it). The aggregate preserves any contradiction,
then any gap. There is no average, no maturity score, no confidence score, no
percentile and no individual performance rating.

### Scoping — why valid work stays valid

The first version of the ordering check cross-producted every event of kind A
against every event of kind B across the whole case. That produced two false
positives immediately, and both were fixed before they reached a fixture:

- **Two services recovering independently.** Service B's restore legitimately
  completes *before* service A's disruption. A global cross-product calls that an
  inversion; it is normal parallel recovery. Recovery rules are now scoped **per
  service**. Guarded by `test_independent_recovery_is_not_serialised`.
- **A pre-release staging verification.** It legitimately happens *before* the
  deployment. Only a verification of the environment that actually ran the release
  has an ordering relation to that deployment, so `DEPLOY_BEFORE_VERIFY` reads the
  same-environment slot only. Guarded by
  `test_pre_release_verification_before_deploy_is_not_an_inversion`.

`case.json` deliberately contains both patterns, so a regression that re-serialises
independent work shows up on the narrative case, not only in a unit test.

## UNKNOWN discipline

An absent input is never turned into a zero, a pass, or a score.

- An event with `observed_at: null` stays **UNKNOWN**, is reported as
  `UNORDERABLE_EVENT`, and is **excluded** from ordering checks. It never defaults
  into position, never becomes "earliest", never becomes satisfied. An ordering
  constraint touching an unknown endpoint reports `UNKNOWN` — neither a pass nor a
  violation.
- The shared register is **never backfilled** from a component's assertion. If the
  register is UNKNOWN and a component asserts a time, that is reported
  (`REGISTER_UNKNOWN_BUT_ASSERTED`) so the export gets reconciled, rather than
  inventing a timeline point nobody recorded.
- `restoration_status` is **derived, never asserted**. There is no input field that
  can claim `DEMONSTRATED`; supplying one is a validation error.
- Interview evidence without artifact corroboration remains UNKNOWN (UIOWA-057's
  rule, consumed rather than re-litigated).
- An empty service list is a validation error, never a pass (UIOWA-057's "empty
  deployment collections are never a pass", restated).
- UNKNOWN survives projection: a dependency verified at an unrecorded time emits
  `"verified_at": null`, not a materialised guess.

## The fixtures are the deliverable

Every fixture is the **same clean base plus exactly one documented mutation**,
produced by `make_fixtures.py`. That is what makes a green result mean something:
when `timeline-disagreement.json` fires and `clean.json` does not, the only thing
that changed is the mutation. `test_fixtures_on_disk_match_the_generator` fails if
anyone hand-edits a fixture and breaks that property.

| Fixture | Mutation | Must fire | Status |
|---|---|---|---|
| `clean.json` | *none* | **nothing at all** | `AGREED` (exit 0) |
| `timeline-disagreement.json` | provenance asserts a deploy time 5 min off the register | `TIMELINE_DISAGREEMENT` | `CONTRADICTIONS` |
| `ordering-inversion.json` | restore completes before the disruption | `ORDERING_INVERSION` | `CONTRADICTIONS` |
| `id-collision.json` | an evidence id reuses an existing event id | `ID_COLLISION` | `CONTRADICTIONS` |
| `unresolved-source-id.json` | a backup cites an evidence id that does not exist | `UNRESOLVED_SOURCE_ID` | `GAPS` |
| `unsupported-recovery-claim.json` | business verification claimed with no source record | `UNSUPPORTED_RECOVERY_CLAIM` | `GAPS` |
| `unknown-timestamp.json` | the deployment event has no observed time | `UNORDERABLE_EVENT` | `GAPS` |
| `environment-difference.json` | the passing verification ran in another environment | `ENVIRONMENT_DIFFERENCE` | `GAPS` |

`test_each_fixture_fires_nothing_else` asserts each fixture fires **exactly** its own
code. **False positives matter as much as misses**: a checker that flags everything
catches every defect and is worthless.

## The narrative case (`case.json`)

One fictional release carrying every element the order names — a known artifact
version, an environment difference, a failed verification, and recovery records —
and showing both a strength and a real gap:

- `fictional-2.3.0` is approved, built, and traceable end to end
  (`DEP-1 → ART-1 → BLD-1 → SRC-1`).
- It **passed verification in `ess-stage`** but was **deployed to `ess-prod`**, where
  the post-deploy verification **FAILED** → `ENVIRONMENT_DIFFERENCE`. A pass in
  another environment is not evidence about the environment that ran the release.
- **Strength** — `SVC-ESS` recovers with a complete evidence chain: backup evidenced,
  dependency verified, business function verified → `DEMONSTRATED`, observed RPO
  50 min and RTO 50 min, both inside target.
- **Gap** — `SVC-RIS` claims its dependency was verified but nobody recorded *when*.
  The claim is reported `UNSUPPORTED_RECOVERY_CLAIM` and the service is held at
  `PARTIAL`. Its observed RPO of 80 min exceeds its 60 min target.
- **Honest absence** — `SVC-IAM` was never exercised, and its backup rests on
  interview evidence only → `backup_status UNKNOWN`, `NOT_DEMONSTRATED`. That is an
  absence of evidence, explicitly *not* a failed exercise.

Note the case is simultaneously **fully traceable and not demonstrably recovered**.
Collapsing those two into one verdict is the mistake this kit exists to prevent.

## Files

| File | What it is |
|---|---|
| `release_recovery_case.py` | the engine: contract, checks, projections, CLI, renderers |
| `case.json` | the narrative case (generated) |
| `fixtures/*.json` | clean control + one fixture per defect class (generated) |
| `make_fixtures.py` | deterministic regeneration of `case.json` and `fixtures/` |
| `test_release_recovery_case.py` | 54 `unittest` cases |
| `out/*` | sample outputs committed so a reviewer can read them without running anything |

## Real vs. draft

**Real and working** — the engine, all eight fixtures, the 54-case suite, the three
projections, the CSV/JSON/Markdown renderers, and the committed `out/` samples. All
of it runs offline on the standard library and is deterministic: every calculation
is against the case's declared `as_of`, never the wall clock, so two operators on
different days get byte-identical output (`test_two_runs_are_byte_identical`).

**Draft / carries a caveat**

- The **contract drift guard**
  (`test_provenance_contract_has_not_drifted_from_the_sibling_lane`) re-reads 057's
  real `packet.schema.json` when that lane is present and fails if the contract
  moved under the projection. It was verified both ways before landing: it passes
  against the live schema, and it fails when a field is injected into a copy. In a
  checkout without the sibling lane it **skips with a stated reason** rather than
  passing silently.
- The projections are **contract-shaped**, not executed through the sibling tools.
  They are asserted against those kits' field lists; nobody has yet piped
  `out/projected_provenance_packet.json` into `provenance.py` and
  `out/projected_recovery_records.json` into `assess_recovery.py` in one run. That
  end-to-end pipe is the obvious next step and is **not claimed as done**.
- The environment component is defined **here**. If a dedicated environment/config
  lane lands later, this view should be re-pointed at it rather than duplicated.
- `ENVIRONMENT_DIFFERENCE` is classed as a *gap*, not a contradiction: the records
  do not contradict each other, the evidence about the environment that ran the
  release is missing. Reasonable people could class it the other way; it is called
  out here rather than buried.

## University inputs that stay UNKNOWN

Nothing below was supplied, and none of it was invented to fill the hole. Each is an
evidence request, not a gap in this tool:

1. Which services are actually in scope for a release/recovery review, and the
   sample boundary — why *these* releases and *these* exercises were chosen.
2. Real RPO/RTO targets, and whether they are agreed commitments or aspirations.
3. The real service dependency graph, including dependencies outside the assessed
   set (this kit reports those as `UNRESOLVED_DEPENDENCY`, never as recovered).
4. Which environments exist, which one actually serves each release, and whether
   pre-release verification runs somewhere representative of it.
5. Whether post-deploy verification is recorded at all, and where those records live.
6. Whether restoration exercises produce a business-function check, or stop at
   technical restore completion.
7. Real evidence locators and their owner roles, and which are artifacts versus
   interview statements.
8. Clock/timezone handling across the exporting systems — the disagreement class
   this kit detects is usually a clock or export problem, not a records problem.

## Boundaries

No real University data, no live systems, no network at runtime, no restore was
performed, and no file outside this directory is read or written. On-screen or
in-file text is treated as **data**, never as instructions. This kit produces no
certification, compliance, procurement or peer-percentile claim, and rates no
individual's performance.
