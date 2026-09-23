# UIOWA-108 — Contractor-transition evidence demonstration

Solicitation 18649. Work order UIOWA-108: *"Connect synthetic staff-role
changes, application ownership, service identities, and runbook updates into
one realistic handoff scenario … The example distinguishes completed access
changes, unresolved ownership, and missing evidence without inserting real
account data."*

Built by seat `OP5-KELVIN` (Claude · Opus 5). Python 3 standard library only,
no network at runtime, deterministic.

---

## Everything here is fictional

Every person, application, service identity, runbook and change record in
`fixtures/` was invented for rehearsal. **This is not a University of Iowa
finding** and says nothing about University access practice. The packet
carries `authority: FICTIONAL_REHEARSAL_ONLY` and the same
`prohibited_interpretation` list as the collection landed for UIOWA-091, so a
downstream tool reading it cannot mistake it for evidence.

Still **UNKNOWN**, listed as evidence to collect later:

- the real joiner/mover/leaver process and who authorises each step
- whether service identities are inventoried anywhere authoritative
- how contractor end dates reach the access-management system, if they do
- what evidence the University can actually export for a completed revocation
- who owns a runbook when its author leaves

---

## The three states, and why they must not merge

A handoff report that collapses these into one green checkmark is worse than
no report, because it is confidently wrong about the one thing somebody will
rely on it for.

| State | Means | Next action |
| --- | --- | --- |
| `COMPLETED` | a dated change record **with an evidence locator** confirms it happened | none; retain the locator for closeout |
| `UNRESOLVED_OWNERSHIP` | the departing contractor still owns it and **no successor is recorded** | name an accountable owner before the last day — this is a live gap |
| `NO_EVIDENCE` | no record establishes either outcome | ask for the change record or export that would settle it |

The distinction that does the most work is between the second and third.
**Unresolved ownership is knowledge** — we know exactly what is wrong and who
is not covering it. **No evidence is the absence of knowledge.** They need
different conversations, and a report that merges them sends the wrong one.

Two cases in the fixture are there because they are the common ways a handoff
report lies:

- **`SYN-RB-001` is marked `COMPLETED` with nothing attached.** Somebody typed
  a word into a status field. That is not evidence, so it classifies
  `NO_EVIDENCE`.
- **`SYN-SVC-002` has a successor named and a request raised.** A named
  successor is a *plan*. Nothing shows the handoff occurred, so it classifies
  `NO_EVIDENCE` too.

### Closure is fail-closed, and there is no percentage

`transition_closed` is true only when **every** item is `COMPLETED`. There is
no threshold, no weighting and no completion percentage anywhere in the
output — a test greps the rendered JSON for `percent`, `score`, `maturity`,
`rating` and `grade` and fails if any appears. One unresolved service identity
is a contractor who still has a way in; averaging it against completed items
produces a reassuring number that describes nothing anybody can act on.

An empty packet does not close by vacuous truth either — nothing to check is
not the same as everything checked.

---

## The realism guard: "without inserting real account data"

A contractor-transition packet is exactly where real-looking account data
leaks into a deliverable. So this is a **hard refusal, not a convention**. Any
of these makes the whole packet undeliverable and the CLI renders nothing:

| Code | Refuses |
| --- | --- |
| `REAL_LOOKING_EMAIL` | any address not under the reserved `.invalid` TLD |
| `REAL_LOOKING_ACCOUNT_NAME` | any `account_name` not prefixed `syn-` |
| `IDENTIFIER_NOT_MARKED_SYNTHETIC` | any id not matching `SYN-<KIND>-<NNN>` |
| `RECORD_NOT_MARKED_SYNTHETIC` | any record not declaring `synthetic: true` |
| `POSSIBLE_REAL_ID_NUMBER` | any nine-digit run in any string field |

`.invalid` is reserved by RFC 2606 precisely so it can never resolve to a real
host — a fictional address under any other TLD is one somebody might actually
try.

**The guard proves it can fail.** `test_the_guard_proves_it_can_fail` takes the
packet that passes clean, injects one real-looking address, and asserts it
flips from deliverable to refused. A guard that has never gone red is worth
nothing. A separate test asserts the clean packet produces **zero** safety
issues, because a guard that fires on everything gets switched off.

**Safety and integrity are treated differently on purpose.** A broken
reference is a *finding* — the report still renders so somebody can see it.
Real-looking account data must not leave the building, so the report refuses
to render at all rather than degrading gracefully.

---

## Run it

```sh
cd revenue/uiowa_rfq_18649_contractor_transition

python3 transition.py --input fixtures/contractor_transition.json --outdir out
python3 transition.py --input fixtures/contractor_transition.json --print
python3 transition.py --input fixtures/contractor_transition_unsafe.json    # refuses
python3 -m unittest -v test_transition
```

Exit codes are a contract: **0** transition closed · **1** open items remain ·
**2** bad input · **3** refused, packet contains unsafe content.

Measured on the synthetic packet:

```
items=6 completed=2 unresolved=2 no_evidence=2 closed=False issues=0
```

Two clean completions with real evidence locators (the strength), two items
nobody owns and two where the record does not support the outcome claimed
(the gaps).

---

## Files

| File | What it is |
| --- | --- |
| `scenario.py` | packet schema, the realism guard, referential integrity |
| `transition.py` | the three-state classifier, report renderers, CLI |
| `fixtures/contractor_transition.json` | the coherent fictional scenario — 3 people, 2 applications, 2 service identities, 2 runbooks, 4 change records |
| `fixtures/contractor_transition_unsafe.json` | deliberately unsafe packet; exists to prove the guard goes red |
| `sample_output/` | committed output; a test fails if it drifts from the code |
| `test_transition.py` | 34 unittest cases |

## What is working vs. draft

**Working and tested.** The three-state classifier and all four of its decision
paths, fail-closed closure, the realism guard including its own failure proof,
referential integrity, all three output formats, and the four CLI exit codes.

**Draft, pending real evidence.** The scenario is fiction. What counts as an
acceptable evidence locator for a completed revocation at the University is
unknown, and the `evidence_ref`-required rule should be confirmed against what
their systems can actually export before it classifies a real transition.

## Scope

This lane produces a worked demonstration. It does not score anyone, rate a
unit's maturity, certify anything, or evaluate an individual — records are
keyed to roles and systems, never to a named person. Join keys (`service` ∈
ESS/RIS/IAM, `synthetic: true`, `authority: FICTIONAL_REHEARSAL_ONLY`,
`synthetic://` locators) match the collection landed for UIOWA-091; this lane
emits those keys and writes into no other lane's files.
