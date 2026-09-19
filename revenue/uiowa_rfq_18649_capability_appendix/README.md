# UIOWA-137 — Evidence-backed technical capability appendix

A two-page proposal appendix in which **no capability claim can be printed
without a recorded demonstration**, plus the generator that enforces that.

Built by seat **OP5-IRONWOOD** (Claude Opus 5) for the RFQ 18649 build board.

---

## The problem this solves

A capability appendix is a marketing document by default. Its natural failure
mode is a claim nobody can check — "robust traceability tooling",
"enterprise-grade evidence organization". Those read well and prove nothing,
and a reviewer has no way to tell them from a claim that is true.

This order asks for *evidence-backed*. The only way to mean that is to make
the document unable to print an unbacked claim.

## The binding rule

A claim is rendered as a capability only when **all six** of these bind:

1. every artifact file it cites exists on disk
2. a run of its demonstration command was actually observed and recorded
3. that run exited zero and produced non-empty output
4. the file digests recorded at observation still match the files now
5. the demonstration command invokes a file the claim itself cites
6. the claim's own wording passes the language check

Fail any one and the claim does not reach the appendix body. It drops to a
separate **Not demonstrated** section with the specific missing element named.
There is no code path that prints a capability with a hole in it, and a test
asserts that a blocked claim's statement text never appears in the body.

### Rule 4 is the one that keeps working after delivery

The digests are of the exact bytes that were executed. If an artifact is
edited after it was demonstrated, its claim **demotes itself** on the next
build — nobody has to notice and nobody has to decide. Two end-to-end tests
cover it: a claim that is demonstrated before the file changes, and the same
claim blocked afterwards with `artifact changed since it was demonstrated`.

### Rule 6 rejects rather than softens

The language check refuses three classes of wording:

- **Marketing adjectives** — `robust`, `seamless`, `enterprise-grade`,
  `comprehensive`, `scalable`, `powerful` and similar. If a sentence cannot
  survive without the adjective, the adjective was doing the work.
- **Unquantified intensifiers** — `significantly`, `dramatically`,
  `substantially`. A comparison without a number is not a claim.
- **Certification and guarantee language** — `certified`, `compliant`,
  `accredited`, `guaranteed`. This engagement does not make that class of
  claim at all, so the generator will not emit it.

Matching is word-boundary anchored, so `complaint` does not trip `compliant`
and `descale` does not trip `scalable` (tested). The check reads the
`business_use` field too, not only the `statement` — the soft claim usually
hides in the justification.

There is also a test that **the generated appendix passes its own language
check**: the document may not contain wording it would reject in a claim.

## Run it

Python 3 standard library only. No installs, no network.

```bash
# executes every demonstration and writes down what actually happened
python3 capability_appendix.py record --observed-on 2026-09-19

# renders the appendix; executes nothing
python3 capability_appendix.py build --outdir out

python3 -m unittest -v test_capability_appendix
```

`record` and `build` are deliberately separate. **`record` is the only part
that runs anything; `build` executes nothing and reads no clock**, so the
document is reproducible from the two JSON files. A test proves it: a register
whose demonstration command would create a marker file is built, and the
marker must not appear.

Verbatim output of the committed run:

```
recorded 6 claim(s): 5 executed, 5 exited zero
  CAP-01 exit=0
  CAP-02 exit=0
  CAP-03 exit=0
  CAP-04 exit=0
  CAP-05 exit=0
  CAP-06 not run: no executable demonstration command declared

claims: 5 demonstrated, 1 not demonstrated
  CAP-06 blocked: demonstration was not run: no executable demonstration command declared
budget: 607 words used of 1000 allowed (1.21 pages at 500 words/page)
```

Verbatim test result: **`Ran 39 tests in 0.119s` — `OK`**.

## What was actually demonstrated

Five capabilities, spanning all four areas the order names. **Each command
below was executed by this seat against the repository and its output
recorded** — these are not figures quoted from another seat's report:

| Claim | Area | Lane | Observed result |
|---|---|---|---|
| CAP-01 | evidence organization | `uiowa_rfq_18649_closeout` | `Ran 7 tests in 0.001s — OK` |
| CAP-02 | traceability | `uiowa_rfq_18649_traceability_rehearsal` | `trace validation: PASS` (8 evidence / 3 findings / 2 recommendations / 5 statements) |
| CAP-03 | comparison | `uiowa_rfq_18649_delivery_metrics` | `Ran 6 tests in 0.006s — OK` |
| CAP-04 | comparison | `uiowa_rfq_18649_recovery_evidence` | `Ran 50 tests in 0.031s — OK` |
| CAP-05 | report preparation | `uiowa_rfq_18649_report_structure` | `Ran 55 tests in 0.147s — OK` |

Three of those five lanes were built by GPT seats (`ZZ-Lattice`, `ZZ-Sol`,
`ZZ-Semaphore`) and two by Claude seats (`OP5-IRONWOOD`, `OP5-GRANITE`). The
binding rule is identical for both, and a test asserts the appendix cites
work from both swarms. Attribution is to a **seat**, never to a person.

**CAP-06 is held back on purpose.** Its artifacts exist and were located, but
this seat did not observe a run of them, so it cannot be printed as a
capability. It is retained in the register and appears in the Not demonstrated
section. That is the behaviour the generator exists to guarantee, and the
shipped artifact demonstrates it rather than describing it.

### Reported commits are marked unverified

Where a commit SHA was reported in the channel it is recorded, and explicitly
marked `not independently verified by this seat`. A SHA copied from a message
is not evidence this seat produced. A test asserts every entry carries that
qualifier. What this seat *can* vouch for is the digest of the bytes it
executed, which is recorded per file in the evidence index.

## The rejection demonstration

`fixtures/rejection_demo_register.json` is a labeled fictional register in
which each of seven claims is broken in exactly one way. Building it produces
`out/rejection_demo/` — **0 demonstrated, 7 blocked**, each naming its reason:

```
BAD-01 wording rejected (marketing language: 'seamlessly'; 'robust')
BAD-02 wording rejected (prohibited certification or guarantee language:
       'certified'; 'compliant'; 'guaranteed')
BAD-03 artifact file(s) not found: tool_that_does_not_exist.py
BAD-04 no observed run recorded for this claim
BAD-05 demonstration exited 2
BAD-06 artifact changed since it was demonstrated: capability_appendix.py.
       The recorded run no longer describes these bytes.
BAD-07 demonstration command invokes some_other_script.py, which the claim
       does not cite
```

## Two pages is arithmetic

The page budget (2 pages × 500 words) is enforced and reported: the committed
appendix uses **607 of 1000 allowed words, 1.21 pages**. Going over is a real
failure of the deliverable, so `build` returns a non-zero exit code rather
than shipping a document that does not fit its own specification.

It **never truncates a claim to fit**. A test sets an impossible budget,
confirms the overage is reported, and asserts every demonstrated claim is
still present in the document. An appendix that quietly drops its last
capability is worse than one that says it is 140 words over.

Verbatim run output and per-file digests live in
`out/capability_evidence_index.md` rather than the appendix body — that is
what keeps the two-page document readable while leaving everything checkable.

## Files

| Path | What it is |
|---|---|
| `capability_appendix.py` | Generator and verifier. Stdlib only. `record` / `build`. |
| `capabilities.json` | The claim register — six claims, one deliberately unrun. |
| `observed_runs.json` | What this seat actually executed, with exit codes, verbatim output and file digests. |
| `fixtures/rejection_demo_register.json` | Fictional register, seven deliberately broken claims. |
| `fixtures/rejection_demo_observations.json` | Paired hand-written observations for the rejection demo. |
| `test_capability_appendix.py` | 39 `unittest` cases including hostile and drift scenarios. |
| `out/capability_appendix.md` | **The deliverable** — the two-page appendix. |
| `out/capability_evidence_index.md` | Verbatim output and digests per claim. |
| `out/capability_claims.csv` | One row per claim, demonstrated or not, with blockers. |
| `out/capability_appendix.json` | Machine-readable result including the budget arithmetic. |
| `out/rejection_demo/` | Generated output of the seven-way rejection fixture. |

## What is real and what is draft

- **Real and working:** the generator, the binding rule, the language check,
  the drift detection, the budget arithmetic, all four output formats, and the
  39-case test suite. Every run output quoted above was produced by this seat
  executing the command shown.
- **Draft:** the claim *wording* is a first pass for a proposal appendix and
  should be reviewed by whoever signs the proposal. The register is the thing
  designed to be edited; the guardrails are the thing designed not to be.
- **Fiction:** everything under `fixtures/`, which exists only to show the
  guards firing. Note that the underlying lanes' own fixtures are synthetic
  too — CAP-01 through CAP-06 demonstrate that the *tooling* runs and what it
  does, not that any result about a real organisation was produced.

## Still UNKNOWN

1. Which capabilities the proposal actually wants to lead with. The register
   is ordered by capability area, not by sales priority.
2. The exact page size, font and margins the submission requires. The budget
   is words-per-page arithmetic (500), which is a stand-in for a real
   typeset measurement and is a single editable number.
3. Whether the reviewer will accept a linked evidence index as part of the
   two-page limit or as a separate attachment. Today they are separate files.
4. The canonical commit SHA for each cited lane at submission time. Reported
   SHAs are recorded but unverified by this seat; the digests are the thing
   that was actually checked.
5. Whether CAP-06's lane has an executable entry point that this seat did not
   find. If it does, recording it promotes the claim with no other change.
