# 30 — Progression method: feasible one-to-two-level improvement paths

How to turn a stated current practice profile into a realistic next one or two maturity
levels, with prerequisites, capability changes, adoption evidence, effort and skill needs,
and observable advancement.

**Everything in this document and its worked examples is synthetic.** The profiles are
assumption sets written to exercise the method. None describes the University of Iowa's
practice, and no level, path or effort figure here is a University baseline, a finding, or a
commitment.

---

## 1. The scale this method plans against

This method does not define a maturity scale. It consumes the anchor contract from
**UIOWA-021** — `maturity_rank`, `maturity_label`, `assessment_status` — and plans against
it.

| level | label |
|---:|---|
| 1 | ad hoc |
| 2 | documented |
| 3 | practised |
| 4 | consistent |
| 5 | measured |

The load-bearing part of that contract is the **evidence-kind cap**: the *kind* of evidence
bounds the level it can support, regardless of how much of it there is.

| evidence kind | supports up to level |
|---|---:|
| `policy_document` | 2 |
| `procedure_document` | 2 |
| `single_observed_instance` | 3 |
| `repeated_instances` | 4 |
| `outcome_measurement` | 5 |

Ten written policies are still zero instances of practice. One observed instance is not a
pattern. Repeated instances are not a measured outcome.

---

## 2. Establish the baseline before planning anything

The baseline is **the highest cap any single stated evidence assumption reaches**. It is
always reported together with the assumptions it rests on, and always described as what the
assumed evidence supports — never as an observation.

**An unestablished baseline produces no path.** If the practice is `unassessed` or
`not_applicable`, or no evidence assumption is stated, the baseline is `maturity_rank = None`
and the method refuses to plan. It does **not** fall back to level 1: "we have not
established this" is not "this is bad", and a route invented from a guessed starting point
is exactly the unverified baseline this method must not present as fact.

The refusal names what would settle it.

### Evidence assumptions must carry a basis

Every assumption records where it came from. An assumption with no stated origin is
indistinguishable from an observation, which is the confusion the whole method exists to
avoid. The tool refuses one without a basis.

---

## 3. Choose a target: one or two levels, no further

A path may gain **at most two levels**. A longer jump is an aspiration, not a path; split it
and plan the first two. A target at or below the established baseline is refused — there is
nothing to advance.

---

## 4. The feasibility test: is the target earned or claimed?

This is the decisive step.

Each step in a path declares the **kind of evidence it would produce**. The path's ceiling is
the highest cap among its steps. **If the ceiling is below the target level, the path is
refused** — the target needs evidence of a kind the path never creates, and no amount of
effort closes that gap.

This is what turns "no aspirational endpoint" from a principle into a check:

> A path proposing to reach level 4 (consistent) by writing a detailed procedure and a
> supporting standard — 22 person-days of genuine work — is **refused**. Documents cap at
> level 2. The refusal names the evidence kinds that could reach level 4:
> `repeated_instances` or `outcome_measurement`.

The refusal is not a judgement about the work. Writing the procedure may be entirely
worthwhile. It just does not reach level 4, and saying it does would be the aspiration.

---

## 5. Advancement must be observable

Every step states what would be **observed** when it is done: a dated record, an export
covering a named population, a sample showing a property. A step whose completion nobody can
check is not a plan, and writing `TBD` does not make it one. The tool refuses the path and
names the step.

A useful test for the wording: could a third party apply it to the artifact and get the same
answer? "Improve the process and raise awareness" fails. "A one-month sample of merges each
shows a recorded reviewer distinct from the author" passes.

---

## 6. Prerequisites

A step may name prerequisites. A prerequisite produced by another step in the same path is
fine. One that no step produces is **refused**, unless it is declared external with an
`EXTERNAL:` prefix — in which case it is surfaced in the output as somebody else's to
deliver, rather than silently absorbed into our plan.

---

## 7. Effort and skills

Each step carries `effort_person_days` and `skills_needed`, both stated assumptions.

Where a step is **unestimated**, the path total is reported as a **floor**, explicitly
labelled, with the unestimated steps named. It is never completed to a round number, and an
unestimated step is never counted as zero effort.

---

## 8. Alternative paths

The same target can usually be reached more than one way. The method carries three variants:

- **`direct`** — the straightforward route.
- **`limited_capacity`** — same target level, less effort, usually by narrowing the
  population covered in the first cycle and writing the scope limit down. The alternative is
  a **different route, not a lower ambition**; the target level is the same.
- **`shared_service`** — uses a capability the groups already share rather than asking each
  to build its own. Typically carries an `EXTERNAL:` prerequisite on the shared service.

---

## 9. Worked synthetic paths

Eleven candidate paths across all four assessment areas — software development, security,
deployment, AI readiness. Six are feasible; five are written to be refused, so each refusal
is demonstrated rather than described.

| verdict | paths |
|---|---:|
| `FEASIBLE` | 6 |
| `BASELINE_UNKNOWN` | 1 |
| `REFUSED_EVIDENCE_CAP` | 1 |
| `REFUSED_ASPIRATIONAL_JUMP` | 1 |
| `REFUSED_NO_OBSERVABLE` | 1 |
| `REFUSED_UNMET_PREREQUISITE` | 1 |

Generate them:

```bash
python3 progression.py                       # print the worked paths
python3 progression.py --markdown-out out.md --csv-out out.csv --json-out out.json
python3 -m unittest -v test_progression.py
```

Full generated output: `examples/worked-paths.md`, `examples/paths.csv`,
`examples/paths.json`.

### The six feasible paths

| path | area | variant | baseline → target | effort |
|---|---|---|---|---|
| `PATH-SYN-SD-01` | software development | direct | 3 → 4 | 7 d |
| `PATH-SYN-SEC-01` | security | direct | 2 → 3 | 5 d |
| `PATH-SYN-SEC-02` | security | limited capacity | 2 → 3 | 2 d |
| `PATH-SYN-SEC-06` | security | shared service | 3 → 4 | 7 d |
| `PATH-SYN-DEP-01` | deployment | direct | 4 → 5 | 8 d |
| `PATH-SYN-AI-01` | AI readiness | limited capacity | 3 → 4 | 1 d floor |

`PATH-SYN-AI-01` is the partial-effort case: its second step cannot be sized until the first
step defines the trigger, so the total is a floor with the unestimated step named.

`PATH-SYN-SEC-06` is the shared-service case: it reaches level 4 by taking membership data
from the central identity service instead of reconciling three spreadsheets, and carries the
external prerequisite that the service exposes an export.

### The five refusals

| path | verdict | why |
|---|---|---|
| `PATH-SYN-SEC-03` | `REFUSED_EVIDENCE_CAP` | Reaches for level 4 with 22 person-days of documents. Documents cap at 2. |
| `PATH-SYN-SEC-04` | `REFUSED_ASPIRATIONAL_JUMP` | Level 2 → 5 in one plan. Gain of 3. |
| `PATH-SYN-AI-02` | `BASELINE_UNKNOWN` | Plans a route from a practice nobody has assessed. |
| `PATH-SYN-SEC-05` | `REFUSED_NO_OBSERVABLE` | "Improve the process and raise awareness" — nothing to check. |
| `PATH-SYN-SD-02` | `REFUSED_UNMET_PREREQUISITE` | Depends on `SD-02-Z`, which no step delivers and which is not declared external. |

---

## 10. What a FEASIBLE verdict does and does not mean

**Does mean:** the baseline is established from stated assumptions, the gain is one or two
levels, the evidence the path would produce can reach the target level, every step's
completion is observable, and every prerequisite is either delivered by the path or visibly
external.

**Does not mean:** a prediction that the work will succeed, an estimate anyone has committed
to, a statement about the University's actual practice, or a claim that the target level is
worth reaching. Whether a given level is the right ambition for a given practice is a
judgement this method does not make.

---

## 11. Inputs still UNKNOWN

- **Every profile.** The six here are assumption sets. Real profiles come from the
  assessment.
- **Every effort and skill figure.** Stated assumptions with no staffing basis behind them.
- **Whether the evidence-kind caps are the right ones.** They come from the UIOWA-021 anchor
  contract as declared in the build channel; that lane owns them and may revise them. This
  method consumes the scale and deliberately does not define a second one.
- **Whether two levels is the right maximum** for this engagement, or whether some practices
  should be planned one level at a time.
- **Which practices are in scope at all**, and who owns each one.
