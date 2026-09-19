# Source notes — what is real, what is fiction, what is UNKNOWN

## The one real external reference

**NIST AI Risk Management Framework** — <https://www.nist.gov/itl/ai-risk-management-framework>

Used here **as a reference for organizing leadership discussion, not as a
certification checklist.** Concretely, that means:

**What is used:** the four core functions — `GOVERN`, `MAP`, `MEASURE`,
`MANAGE` — as a sort key on the policy records, so a leadership conversation
can be grouped by function rather than by policy number.

**What is deliberately NOT used, and why:**

| Not done | Why |
|---|---|
| Subcategory-level mapping (e.g. mapping a cell to a specific numbered subcategory) | This tool ships with no copy of the framework document and would have to invent identifiers to appear thorough. Subcategory mapping is **UNKNOWN** here. If the University wants it, it is a scoped piece of work against the actual publication, not something to guess at. |
| Any "RMF coverage %" or profile-completeness figure | The AI RMF is voluntary guidance. There is nothing to be a percentage *of*, and such a figure reads as a conformance claim. |
| Any statement that the organization is or is not "aligned to", "compliant with", or "conformant to" the AI RMF | The AI RMF is not a certifiable standard and this is not a certification body. |
| Any maturity tier or readiness level | Not produced anywhere. `score()` raises `ScoreRefused`. |

The AI RMF appears in exactly three places in the code: the URL constant, the
four function names, and a validation rule that rejects any policy record
naming a function outside those four. A test (`test_rmf_is_reference_only`)
asserts the last of these.

## Everything else is fiction

**Example State University** is invented. So is every policy, policy number,
task, evidence record, locator, date, and open question in `fixtures/`.

The fiction is labeled at four levels so it cannot be quoted out of context:

1. Every evidence `locator` string begins with `FICTIONAL:`.
2. Every policy `source_doc` string begins with `FICTIONAL:`.
3. A `fiction_notice` field is written into `findings.json` and printed by the
   CLI on every run.
4. `matrix.md` and `WORKFLOW_EXAMPLES.md` both open with a fiction banner.

**No record here describes the University of Iowa**, its policies, its systems,
its staff, or its practices. Nothing in this lane was gathered from the
University, and nothing in it should be read as a finding about the University.

The fixtures were written to be *internally consistent and argumentative* —
they contain a genuine strength (a merge gate enforced in configuration), a
genuine gap (AI prompt/response logs with no classification and indefinite
retention), an unresolvable interpretation question, a practice with no policy
behind it, and an incomplete piece of fieldwork. A fixture set where everything
passes teaches nothing about whether the instrument works.

## University inputs that are UNKNOWN

These are not gaps in the tool. They are inputs only the University can supply,
and the tool is built to hold them as UNKNOWN rather than fill them in:

- **The actual policy inventory.** Which AI, data, security, procurement, and
  records policies exist; their real status (active / draft / superseded); their
  real effective dates; and which of them the University considers to reach AI
  use at all.
- **Policy ownership by role.** `owner_role` is fictional throughout. Real
  ownership determines who can answer the open questions.
- **The real task list.** The nine tasks in `fixtures/tasks.json` are a plausible
  set for a university IT organization, not an observed one. Which ordinary
  development tasks actually involve AI, and how often, is unknown.
- **Whether prompt text and retrieval context are institutional data.** This is
  `Q-01`, it is marked `blocking: true`, and it is genuinely undecidable from
  outside. It is the clearest example of an input that must not be guessed.
- **Retention and records-schedule authority for AI prompt/response logs** (`Q-05`).
- **Accountability for AI-assisted work by student employees** (`Q-03`) —
  a question with employment and academic dimensions this tool has no view into.
- **Scope of "AI tool" for procurement** — whether AI features enabled inside
  already-contracted products are in scope (`Q-04`).
- **NIST AI RMF subcategory mapping**, as above.
- **Evidence-collection completeness.** In this fixture set, 4 of 15 cells were
  never assessed and 1 is blocked. In a real engagement those numbers are a
  property of the fieldwork, and the tool reports them rather than hiding them.

## What is working code vs. what is a draft

**Working and tested** (36 unit tests, all passing):

- `policy_matrix.py` — loading, validation, cell resolution, the reading table,
  the summary, the refusals, and all four output renderers.
- `fixtures/` — the four fictional input files; they load clean and resolve to
  a stable matrix.
- `sample/` — real output from a real run, regenerable byte-for-byte.

**Draft / would change on contact with a real engagement:**

- The task list and policy list are illustrative. A real engagement replaces
  `fixtures/` wholesale; the code does not change.
- The `READING_META` prose (the "means" strings) is written for a leadership
  audience and would be edited to the client's vocabulary.
- `WORKFLOW_EXAMPLES.md` narrates *this* fixture set. Real narratives get
  written against real cells.

**Explicitly out of scope and not attempted:** any real University finding,
any live data, any outreach, any scheduling, any recommendation about a
specific vendor or product, any legal or compliance opinion.
