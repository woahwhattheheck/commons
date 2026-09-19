# Fictional workflow examples for leadership discussion

> **FICTIONAL DATA.** Example State University is an invented organization.
> Nothing below describes the University of Iowa or any real institution,
> policy, system, or person. These narratives exist so leadership can argue
> with a *concrete* case instead of an abstraction.

Each example walks one ordinary development task from start to finish and
stops at the point where the policy question actually bites. Every claim ties
back to a row in `sample/matrix.csv`, so a reader who disagrees with the
narrative can go look at the underlying axes.

Three things are kept separate throughout, and leadership should keep them
separate too:

| | |
|---|---|
| **Stated policy** | What is written down, and whether it binds. |
| **Implementation evidence** | What the assessor actually observed. |
| **Open question** | What the University must decide before anyone can judge. |

---

## Example 1 — The review gate that works, and the disclosure that rides on it

**Cells:** `TSK-02 × POL-AI-01` → `ALIGNED` · `TSK-02 × POL-SEC-07` → `ALIGNED`

A developer on the Enterprise Applications team drafts a permissions fix with
an IDE assistant. They open a pull request. The PR template (`EV-001`) has an
AI-assistance disclosure checkbox in section 4; they tick it. Branch protection
(`EV-002`) will not let the branch merge without the `sdlc/named-reviewer`
check and one approving review. A second engineer reviews and merges.

**Why this is the strongest thing in the assessment:** the control is in
*configuration*, not in convention. The assessor did not ask anyone whether
they follow the rule — they exported the branch protection settings and read
14 of 14 sampled PRs. Nobody can quietly stop doing this without changing a
setting that leaves a record.

**What leadership should notice:** the disclosure checkbox is doing work that
no policy actually requires. POL-AI-01 requires acceptable use; it does not
require the disclosure. The checkbox is a local practice that happens to give
the University its only population-level view of where AI-assisted code is
entering the codebase. If a future template revision drops it, nothing is
violated and the visibility disappears.

---

## Example 2 — The gap: logs nobody classified

**Cells:** `TSK-08 × POL-SEC-07` → `STATED_NOT_PRACTICED` ·
`TSK-08 × POL-DATA-03` → `STATED_NOT_PRACTICED`

Three applications have AI features switched on. Each writes the prompt text
and the model's response into the ordinary application log store. The assessor
went and looked (`EV-006`): retention on that store is set to `indefinite`.
They then asked for the data classification assigned to it (`EV-007`): none
has been assigned and no steward is recorded.

**This is a real finding, and it is worth being precise about why.** Two
separate *active* policies reach this task. SEC-07 requires defined retention
for application logs. POL-DATA-03 requires a classification and a steward for
institutional data. Neither is a draft. Neither is ambiguous about whether it
applies to an application log store. Somebody checked, and the practice is
absent.

**The gap is in practice, not in the policy library.** This distinction
matters for what leadership does next. The instinct on seeing an AI finding is
to write an AI policy. Another policy would not have changed this cell — two
already say the right thing. What is missing is that nobody is executing
against them for this particular log stream, most likely because the stream
did not exist when either policy was written.

**Open question Q-05 (non-blocking)** asks which retention schedule governs
these logs. Note that it does *not* block the finding: neither schedule is
being applied, so the gap stands whichever answer comes back. Q-05 determines
the remediation target, not whether there is one.

---

## Example 3 — The one the assessor cannot answer: does a prompt count as data?

**Cell:** `TSK-05 × POL-DATA-03` → `BLOCKED_ON_CLARIFICATION`
(`reading_if_unblocked`: `ALIGNED_INDIRECT`)

An engineer needs to supply institutional records as retrieval context for an
AI feature. They file a data extract request on form DX-REQ (`EV-011`), which
has been in use since 2022. The form captures requester, source system, and
data class. Six completed 2026 submissions were inspected. The process is
followed.

The form has no field for AI prompt or retrieval use, because it predates
institutional AI use entirely.

**Here is why this cell is reported as blocked rather than resolved.**
POL-DATA-03 defines institutional data handling duties for data *at rest and
in transit between University systems*. It does not say whether prompt text and
retrieval context transmitted to an external AI vendor fall inside that
definition. Both readings are defensible from the text:

- If **prompt text is in scope**, then DX-REQ is the wrong instrument — it
  records a data class but nothing about onward transmission to a vendor — and
  every AI retrieval path in the institution needs a handling decision.
- If **prompt text is out of scope**, then current practice is already correct
  and the form is doing exactly what it should.

The assessor has no basis to pick. Picking would mean inventing University
policy and then assessing the University against the invention. So the cell
returns `BLOCKED_ON_CLARIFICATION` and **Q-01** goes to the Institutional Data
Governance Council.

**What leadership gets for free here:** the evidence that was gathered is not
thrown away. `evidence_axis` on this row still reads `EVIDENCED_INDIRECT` and
`reading_if_unblocked` still reads `ALIGNED_INDIRECT`. When the Council
answers, one field changes. Nobody re-does the fieldwork.

---

## Example 4 — The practice with nobody's name on it

**Cell:** `TSK-09 × (no policy)` → `UNDOCUMENTED_PRACTICE`

A vendor changes the underlying model behind a product the University already
uses. No announcement reaches the service owner. Two engineers in Platform
Engineering maintain a wiki page called "vendor model watch" (`EV-009`). It has
dated entries for 2026-04-02 and 2026-07-15, each recording the version change,
the regression suite being re-run, and the outcome.

This is good work. It is also the single most fragile thing in the assessment.

- No policy requires it.
- No role is accountable for it — the task's `accountable_role` field reads
  *"Platform Engineering (practice observed; no role is named for this task in
  any policy reviewed)"*, which is the honest entry.
- It exists because two specific people decided it should.

**Why the tool reports this as a strength and not a compliance failure.** A
conformance-shaped assessment would mark this row red: no policy, no control,
no owner. That reading is wrong twice. It is wrong about the present, because
the practice is demonstrably happening and is documented with dates. And it
punishes the only team that noticed the problem, which is a reliable way to
stop teams from telling assessors things.

**The discussion for leadership is continuity, not compliance.** The question
is not "why is there no policy" — it is "what happens to this when either of
those two engineers changes roles." That is a different conversation and it
produces a different action.

---

## Example 5 — What "everyone says they do it" is worth

**Cells:** `TSK-01 × POL-AI-01` and `TSK-03 × POL-AI-01` →
`STATED_PRACTICE_UNCORROBORATED`

Developers state in a group interview (`EV-004`) that they never paste
institutional data into the coding assistant. The Service Desk Lead states
(`EV-010`) that AI ticket summaries are always read against the original thread
before routing.

Both statements may well be true. Neither is evidence.

The tool records them at `ASSERTED_ONLY` and the cells read
`STATED_PRACTICE_UNCORROBORATED` — which counts as **neither a gap nor a
strength**. This is deliberate and it is the second-most-important rule in the
design after the UNKNOWN rule: an interview assertion is never promoted to
implementation evidence. `ASSERTED_ONLY` sits below `EVIDENCED_INDIRECT` in the
ordering, and a test asserts that no combination of policy status and assertion
ever produces a strength.

**Contrast with the neighbouring cell.** `TSK-01 × POL-DATA-03` is a *gap*
(`EV-005`): the assessor searched the assistant admin console, the IDE policy
configuration, and the DLP rule set, and found no control restricting data
classes in assistant prompts. So on the same task, the same day, the
organization has one cell where staff say the right thing and one cell where
the mechanism that would make it true is absent. Both are reported. Neither is
allowed to cancel the other out.

---

## Example 6 — Practice ahead of policy, and the cell that is nobody's fault

**Cell:** `TSK-02 × POL-AI-04` → `PRACTICE_AHEAD_OF_POLICY`

POL-AI-04 is a draft, circulated 2026-06-20 and not ratified. It would require
the human who accepts AI output to record what they verified. In 9 of 14
sampled PRs, reviewers already leave a "verified against ticket acceptance
criteria" note naming what they checked (`EV-003`).

The team is doing the thing the draft would require, before it requires it.

The tool will not call this `ALIGNED`, because alignment to a document that
binds nothing is not a meaningful statement. It will also not call it a gap,
which would be absurd. `PRACTICE_AHEAD_OF_POLICY` is its own reading and it
counts as a strength.

**Open question Q-02 (non-blocking)** asks whether current practice should be
described against the draft at all, or only against the active POL-AI-01. It is
non-blocking on purpose: what the assessor observed can be recorded either way,
so the fieldwork is not held hostage to a governance decision. Answering it
before the final report avoids re-litigating three cells in the readout.

---

## Reading the summary honestly

This run produces:

```
cells=15 assessed=10 not_assessed=4 blocked=1 gaps=3 strengths=5
```

**Four of fifteen cells were never assessed.** That is not a finding about
Example State University; it is a fact about how far the fieldwork got. The
tool forces a caution line into every output saying so, and excludes those
cells from both the gap count and the strength count.

The specific case worth showing leadership is `TSK-07 × POL-SEC-07`. There *is*
an evidence record for it (`EV-012`), with a date, an observer, and a locator.
It says the walkthrough of the release approval record was scheduled for
2026-08-25 and did not take place. A tool that counts records would score this
cell. This one reads the `checked` flag, sees `false`, and returns
`NOT_ASSESSED`.

Release approval may be excellent. It may be absent. Nobody looked, so the
honest answer is that we do not know — and "we do not know" is written into
the deliverable rather than rounded to whichever neighbour is convenient.
