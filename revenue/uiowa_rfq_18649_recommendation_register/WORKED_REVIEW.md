# UIOWA-038 — Worked recommendation review

**SYNTHETIC · INTERNAL DEMO · DRAFT, NOT A UNIVERSITY ASSESSMENT**

This is a readable worked example of the recommendation register. It can be used
without running software. Every finding, practice proposal, role, quantity and
phase below is fictional. Nothing here is an approved recommendation, staffing
promise, finding of fact about the University, or authorization for contact.

The executable implementation and tests are retained separately in
[PR #16346](https://github.com/woahwhattheheck/commons/pull/16346), original candidate
`32af7fac5013e6d19fa62357b4256a35237a77ab`. This document's publication does **not**
claim that executable PR is merged or that its hosted workflows succeeded.

## The decision the example makes visible

A single proposed practice can address several findings in several groups without
becoming several pieces of work. In the example, one common intake record serves
both ESS and RIS. Counting it once per linked finding would inflate the apparent
workload. Conversely, a second recommendation can serve the same finding while
requiring genuinely different work; merging solely because the finding is shared
would hide that work. Stable recommendation IDs preserve both distinctions.

**Observed fictional register:** 5 distinct recommendations, 6 distinct finding
records, 9 finding links, and 4 prerequisite edges. Four recommendations have
explicit effort ranges; their subtotal is 6–12 person-days. One estimate is unknown,
so **the total remains UNKNOWN**, not 6–12 and not 6–12 plus zero.

## Read the five recommendations

| ID | Proposed practice change | Scope | Linked findings | Effort assumption | Proposed phase | Prerequisites |
|---|---|---|---|---|---|---|
| REC-SYN-01 | Use one intake record with an observable acceptance criterion | ESS/software and RIS/software | F-SYN-01, F-SYN-02 | 2–4 person-days | 0–90 | None declared |
| REC-SYN-02 | Rehearse deployment and rollback verification against that record | ESS/software and ESS/deployment | F-SYN-01, F-SYN-03, F-SYN-06 | 3–6 person-days | 90–180 | REC-SYN-01 |
| REC-SYN-03 | Review a departed contractor role across the relevant system inventory | IAM/security | F-SYN-04 | UNKNOWN | UNASSIGNED | REC-SYN-01 |
| REC-SYN-04 | Record an unresolved AI-use evidence request in an existing review | RIS/ai_readiness | F-SYN-05 | 0 incremental person-days, explicitly assumed | 0–90 | None declared |
| REC-SYN-05 | Review whether shared records reduce cross-group clarification | ESS/software and RIS/software | F-SYN-01, F-SYN-02 | 1–2 person-days | 180+ | REC-SYN-01, REC-SYN-02 |

Department names are unknown in every scope cell. Multi-group scope does not make
one group the owner. The roadmap retains both `owner_groups` and has
`owner_group=null` for REC-SYN-01 and REC-SYN-05. The human owner-role field is a
separate proposal, not a named person's acceptance.

### Why the effort numbers are not evidence

REC-SYN-01 assumes two facilitated sessions plus a template rehearsal. REC-SYN-02
assumes one sandbox rehearsal and follow-up review. REC-SYN-05 assumes two
retrospective review sessions. These are invented planning bases, not measured
estimates or a statement that the necessary people are available.

REC-SYN-04 assumes **zero incremental effort only because a review slot already
exists in this scenario**. The review slot itself is not free. A zero value without
that basis should not be substituted for an absent estimate.

The subtotal is `(2 + 3 + 0 + 1)` through `(4 + 6 + 0 + 2)` = **6–12**. No multiplier
is applied for finding links, groups or assessment dimensions. Summing independent
ranges does not establish a confidence interval, completion date or feasible plan.

## Trace from a finding without duplicating the register

| Fictional finding | Recommendations that reference it |
|---|---|
| F-SYN-01: intake example lacks a stable acceptance criterion | REC-SYN-01, REC-SYN-02, REC-SYN-05 |
| F-SYN-02: another intake example uses a different format | REC-SYN-01, REC-SYN-05 |
| F-SYN-03: deployment trace lacks a business-function check | REC-SYN-02 |
| F-SYN-04: contractor departure lacks a post-change system observation | REC-SYN-03 |
| F-SYN-05: AI-use interview has no example artifact | REC-SYN-04 |
| F-SYN-06: rollback discussion lacks a retained verification result | REC-SYN-02 |

These statements are fixtures written to exercise the tool. The shared
`SYNTHETIC-ILLUSTRATION` reference is not six independently collected artifacts.
A reference existing in a record does not establish authenticity or corroboration.

## Four useful reviewer interventions

**Add another finding link to REC-SYN-01.** The link count increases by one, while
the recommendation count and effort subtotal stay unchanged. Check whether the new
finding falls inside the declared group/dimension scope; an out-of-scope link is
named, not silently accepted as coverage.

**Plan REC-SYN-03.** Its owner role, effort range, maturity step and phase are all
unknown. Supply an explicit proposal and its basis rather than cloning values from
REC-SYN-01. A phase of null stays UNASSIGNED. Neither a dependency nor a policy
supplies the missing planning decision.

**Inspect REC-SYN-05 in the roadmap.** Both prerequisite IDs and the `180+` phase
must remain present. The export is a projection, not a new plan. Cycles, same-phase
order and available capacity belong to the existing dependency/planning analysis.
This document has not run that sibling engine or established plan feasibility.

**Change a proposal through the source, not the display.** Edit canonical JSON or
the typed CSV tables, then regenerate report and roadmap views. Altering only a
field in a derived view is refused on import; the tool must not quietly ignore
that change and resurrect the old proposal.

## What a complete record carries

A recommendation carries its ID, practice change, scoped cells, finding IDs,
impact hypothesis, effort range with unit and basis, required skills, prerequisite
IDs, owner role, outcome measure with baseline/target/unit/basis, proposed maturity
step, proposed phase and assumptions. Both report JSON and roadmap JSON retain the
whole source register and its digest, including fields not shown in their tables.

For example, REC-SYN-02 has an invented baseline of zero and target of three
retained verification examples. Its basis explicitly identifies both as scenario
assumptions. REC-SYN-01 has no numeric baseline or target. Those null values do not
become zero merely because another recommendation contains a number.

The maturity-step text describes proposed practice development, not an awarded
numeric maturity score. No component here recommends a commercial product or
vendor or awards an institutional maturity rating.

## Editing and failure interpretation

The retained implementation can export a new folder containing canonical JSON,
metadata JSON, findings CSV, recommendations CSV, report JSON, roadmap JSON and
readable Markdown. Each decoded CSV cell is itself JSON: a string is `"90-180"`,
a list is `["REC-SYN-01","REC-SYN-02"]`, a known number is `0`, and unknown is
`null`. Literal text quotes are retained. Empty cells are not interchangeable with
null. Editing ordinary pretty-printed register JSON is usually easier for nested
objects.

The example's `check` exit is 1 because four planning fields remain unresolved.
A successful export may still contain those unresolved items. Exit 0 means only
that the requested operation completed or that the limited data check found no
items. It never means buyer approval, evidence truth, a feasible schedule or a
completed assessment.

Existing output files and directories are refused. Partial write failures preserve
already-created output rather than recursively deleting evidence. The operator
must use a controlled workspace; concurrent hostile parent-directory replacement,
large-volume production operation and spreadsheet-application behavior beyond CSV
parser round-trips are not established by the retained tests.

## Reproducibility and state

The pinned candidate's actual local runs were **56 normal tests and the same 56
under `python -O`, with no failures or skips**. These are 56 distinct test methods,
not 112 different tests. The runtime-only suite has 50; structural-schema checks
add 6. The tests include actual normal/optimized CLI processes from an unrelated
working directory and both complete-view round-trips.

Exact executed bindings:

| Object | Git blob |
|---|---|
| register.py | 966ec8a59dfbc58675994042a19c9fc2beb79813 |
| test_register.py | ebc77c6c46b74b7e892770053c7458c78f1a94fb |
| test_schema.py | abe74eb7e571df9ba3f99f461e2f7e83ccbb46ea |
| register.schema.json | 950bc83c5526e7cda0471f5b138f70d3eb47e466 |
| examples/synthetic_register.json | 47dceb68c03398f81b04cec5ca7ea4740498e51c |

Native GitHub tree readback matched these executed hashes. Provider CI and merge
state are separate live facts recorded on PR #16346; neither is inferred from the
local tests or this walkthrough's own publication.

Workshare vocabulary credit stays with its existing authors. UIOWA-115 dependency
checker credit stays with OP5-JUNIPER. This register and walkthrough were built by
ZZ-KESTREL-Q9D / GPT-6 Astra Pro under operation
`uiowa038-recommendation-register-kestrelq9d-20260919`.

Continuation and original work order:
https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824436619569
