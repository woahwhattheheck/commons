# Q&A refusal contract — evidence lookup that can say "not supported"

**UIOWA-089C.** A complement to the UIOWA-089 discussion/Q&A kit, not a replacement
for it. 089 answers questions the evidence supports. This lane covers the part that
decides whether a readout survives contact with a room: **what the kit does with a
question it cannot answer.**

Everything in `fixtures/` is **synthetic and fictional** — invented organisations,
documents, numbers and quotations, for rehearsal. **Nothing here is a University of
Iowa finding and nothing here should be presented as one.** The real University
inputs are listed as UNKNOWN at the bottom of this file.

## Why a lookup tool needs a refusal contract

The obvious build is: index the evidence, retrieve the nearest three chunks for any
question, write a paragraph on top of them. That pipeline **can never say "I don't
know"**, because top-k retrieval is never empty. Ask it where the University ranks
against its peers and it returns the three most peer-adjacent sentences in the corpus
and answers confidently. The evidence did not contain the answer; the shape of the
system produced one anyway.

So the index here does not produce answers. It **routes**. Every sentence a reader
sees was written against specific evidence IDs and is **re-verified against that
evidence on every lookup** — not once at authoring time, because evidence can be
removed or re-scoped later and a build-time check would keep serving the old answer.
A record that fails verification is **withheld**, not degraded.

## The distinction the whole kit rests on

> "We found no evidence of X" is a statement about **our search**.
> "X does not happen" is a claim about the **University**.

The first is supportable from an assessment. The second never is. And absence is not
one state but three, which the kit refuses to let share a sentence shape:

| Claim type | Means | Support required |
|---|---|---|
| `OBSERVED_PRESENT` | we looked, we found it | ≥1 cited evidence ID |
| `ABSENT_IN_SEARCHED` | we looked **in a named scope** and did not find it | `searched_evidence_ids` + `search_scope`; area must be in `areas_examined` |
| `NOT_ASSESSED` | we did not look | **zero** citations — claiming any is a contradiction |
| `CONTESTED` | evidence disagrees with itself | ≥2 items with different `position` values |

Collapsing `NOT_ASSESSED` into `ABSENT_IN_SEARCHED` is the failure that actually
ships. "No evidence of restoration testing" reads identically whether we reviewed
every runbook and found none, or never asked. One invites a follow-up question; the
other closes it.

Enforcement is deliberately **two-sided**. A structural check catches the author who
forgot a field. A phrasing check catches the author who filled the fields in
correctly and then wrote the sentence anyway. Only the second catches the real
failure, because **the structured field is not what gets read aloud in the room — the
sentence is.** Verbatim, on a bad draft:

```
ABSENCE_STATED_AS_FACT: 'there is/are no ...' states absence as a fact about the
University; an assessment can only report absence from what it searched
```

Notably, an `ABSENT_IN_SEARCHED` claim is also rejected when its area is **not in the
engagement's `areas_examined`**. That claim can be perfectly worded and still wrong:
you cannot report finding nothing in a place you never entered.

## Hostile questions: neither deflected nor answered

Three are in the fixture, each a thing a director says out loud. **Both failure modes
are failures** — inventing a number, and "that's outside our scope." A boundary
response is only valid when it carries all three parts, and the resolver rejects one
that does not:

- **`cannot`** — what this instrument cannot produce, plainly
- **`requires`** — what would actually be needed to produce it
- **`can_say_instead`** — ≥1 real claim, with real evidence IDs, addressing the
  information need behind the question. A boundary with zero supported claims is
  caught as `BOUNDARY_WITHOUT_SUBSTANCE`. That check is what separates an answer from
  a dodge.

| Question | Boundary | What it says instead |
|---|---|---|
| "Where do we rank against peer institutions?" | `B-001` | A ranking needs a peer dataset: same questions, same way, named comparable institutions, matched denominators. One organisation has no percentile. |
| "Which team is the worst?" | `B-002` | Coverage is uneven by design, so a ranking would partly measure *where we looked*. A thinly-evidenced group looks weak because it is thinly evidenced — a property of the assessment, not the team. |
| "Does this make us compliant?" | `B-003` | An audit needs a named framework, a complete population, tested controls, and an auditor with standing. This sampled documents and interviewed five people. |

## Run it

```
python3 cli.py audit                                  # verify every record
python3 cli.py drill                                  # route the whole question bank
python3 cli.py ask "Has RIS tested restoring from backup?"
python3 cli.py ask "Which team is the worst?"
python3 cli.py ask "What is the uptime SLA for the student information system?"
python3 cli.py ask "Which team is the worst?" --json  # machine-readable
python3 cli.py explain "what is the mean time to recovery for RIS"
python3 cli.py claim-types
python3 -m unittest test_qa.py                        # 57 tests
```

Python 3 **stdlib only**. No pip installs, no network at runtime, no model calls. The
index is tf-idf with naive plural stripping — no embeddings, no synonyms — so every
routing decision is inspectable by hand and `explain` prints the arithmetic.

Real audit output on the worked packet:

```
evidence items : 11    answer records : 6
boundaries     : 3     declared gaps  : 2
areas examined : 11 of 12 cells
RESULT: PASS - 0 findings.
```

Real output on the deliberately-broken packet (`fixtures/packet_defective.json`, 12
planted defects): `RESULT: FAIL - 23 finding(s)`.

## Routing, and the two gates

Both must pass before a record is served:

- **score** — tf-idf similarity, guards against noise
- **coverage** — the idf-weighted fraction of the question's own distinctive terms
  the candidate actually contains

**Coverage carries the weight.** Score is relative — the best of a bad field still
wins. Coverage is absolute: if a question asks about "peer percentile ranking" and the
candidate contains none of `{peer, percentile, rank}`, it does not matter that it
outscored the corpus. Thresholds are constants at the top of `qa.py` and are printed
in every routing trace; a threshold nobody can see is a threshold nobody can argue
with.

Resolution order is **trigger boundary → answer → similarity boundary → declared gap
→ refusal**. Being routed is not being answered: when coverage is below `FULL_COVERAGE`
the answer carries `does_not_address`, naming the parts of the question the evidence
does not speak to.

## Three defects this found in its own build

Reported because they are the parts that are easy to claim and hard to get right.

1. **A lecture instead of an answer.** Boundaries originally resolved first. Then
   `what is our strongest practice` → `OUT_OF_SCOPE B-002`: it shares exactly one rare
   word, `strongest`, with the ranking boundary's variants, and one rare shared word
   clears a coverage bar. A reader asking something the evidence directly answers got a
   lecture about not ranking teams. **Over-refusing is a real failure, not the safe
   side.** Fixed by resolution order; regression test
   `test_a_legitimate_question_is_not_lectured`.
2. **"We never looked" was unreachable.** `is IAM ready for AI` fell through to the
   generic refusal. The packet *had* a `NOT_ASSESSED` claim for exactly that cell,
   buried in a coverage answer with no question variants pointing at it — so the kit
   said "I don't know" when the truthful answer was "descoped at kickoff, nobody
   looked." Promoted to its own record `A-006`.
3. **The trigger list could rot silently.** The first version of the guard used an
   absolute idf floor — and idf is relative to corpus size, so it stopped working on a
   smaller packet and the test caught it failing. Replaced with the harm itself: a
   trigger term may not appear in any **answer** record's question variants, plus a
   document-fraction ceiling. Size-independent.

## What is real and what is draft

**Real and working:** the resolver, the two-sided uncertainty-language contract, the
support verifier, the keyword index, the boundary contract, the CLI, both fixtures,
and the 57-test suite. All output in this README is copied from actual runs.

**Draft / deliberately narrow:** the question bank is 11 records, enough to exercise
every path, not enough to cover a real readout. The phrasing checker is regex over a
curated pattern list — it catches the constructions assessors actually reach for, and
it will not catch every possible way to assert a fact. It is a **guard, not a proof**:
a determined author can still write a supported-looking sentence that overstates. The
structural checks are the harder floor.

**Not attempted:** no model calls anywhere; no scoring, maturity rating, percentile,
certification verdict or individual/team performance rating is produced by any path in
this code, and the fixtures contain none.

## University inputs still UNKNOWN

Everything below must come from the engagement before any of this is used for real.
Each stays UNKNOWN in the meantime — none becomes a zero, a pass or a default.

- The actual `assessment_scope`: which group-by-area cells the engagement enters, and
  which are descoped. **This is load-bearing** — `ABSENT_IN_SEARCHED` is checked
  against it, so a wrong scope list turns "we never looked" into "we found nothing."
- The real evidence register: document IDs, locators, versions, coverage levels, and
  which items are search-scope records rather than positive evidence.
- The real question bank — what leadership and practitioners actually ask, which is
  the only way to know whether the boundary trigger lists are right.
- Whether the engagement's own scope language permits the three boundaries as worded,
  or narrows them further.
- Cost, licence and FTE figures (`G-001`, `G-002` are declared gaps precisely because
  they cannot be inferred from usage or commit evidence).

## Interfaces for other lanes

`cli.py ask ... --json` emits `{resolution, record_id, claims[], boundary,
evidence_request, evidence_ids[], does_not_address[], routing_trace[], defects[]}`.
`resolution` is one of `ANSWERED` / `OUT_OF_SCOPE` / `NOT_SUPPORTED` / `KIT_DEFECT`.

Consume `evidence_ids` and `claim_type` directly rather than scraping the prose —
`claim_type` is what keeps an absence from being read as a finding downstream. The
089 kit's lookup records can adopt this contract by adding `claim_type`,
`searched_evidence_ids` and `search_scope` to their answer entries; `qa.QAKit.audit()`
then validates them unchanged.
