# UIOWA-130 — delivery acceptance criteria mapped to actual artifacts

**Artifact conformance evidence only.** The workshare these criteria come from is
**PROPOSED / NOT ACCEPTED**. Nothing in this package represents that the University of
Iowa accepted any conclusion, that a subcontract was executed, or that any payment
occurred. The supporting fixtures in the bound lanes are synthetic and are not
University findings. That rule is enforced by a test.

Built by seat `OP5-BASALT` (Claude, Opus 5) against work order UIOWA-130.

## What it does

Reads the real `ACCEPTANCE_EXHIBIT.md`, extracts its **17 numbered acceptance criteria**
(§5.1–5.3) and **20 deliverable items** (§4.1–4.3), runs a declared content check for
each one against artifacts actually on disk, and answers the only question that matters:
*which of these can a reviewer actually see demonstrated, and which still need real
engagement evidence?*

It is **strictly read-only** against every other seat's lane. A test copies the bound
lanes, builds the index, and asserts that not one file digest changed.

## How it differs from UIOWA-100 / UIOWA-101

Those index lanes by **entry point** — what can I run. This comes from the other end:
it starts from the contractual acceptance criteria and asks what artifact demonstrates
each. So the checks are **content assertions**, not "the test suite passed":

- §5.1.3 demands a register schema that can identify *source, custodian/owner, evidence
  reference, authorization/provenance, observation/currentness, content digest* — the
  check reads the real register's columns and **names the concepts with no column**.
- §5.1.1 and §5.2.2 demand the full 12-cell frame — the check counts the cells.
- §5.2.3 demands that unresolved evidence cannot promote a cell — the check looks for a
  row carrying outstanding evidence *and* a supported state, and fails if it finds one.

A lane can have a green test suite and still fail these. That is the point.

## How to run it

Python 3 standard library only. No installs, no network.

```bash
cd revenue/uiowa_rfq_18649_acceptance_map

python3 build_index.py --revenue-root .. --out output
python3 -m unittest test_acceptance_map          # 26 tests
python3 exhibit_parser.py ../uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md
```

If you check the repository out somewhere the lanes are not the parent directory, set
`UIOWA130_REVENUE_ROOT=/path/to/revenue` for the tests.

## Actual execution results

```
ARTIFACT CONFORMANCE EVIDENCE ONLY. The workshare this index refers to is PROPOSED / NOT ACCEPTED. Nothing here represents that the University of Iowa accepted any conclusion, that a subcontract was executed, or that any payment occurred. Supporting fixtures are synthetic and are not University findings.

exhibit        uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md
               sha256 f6bc85c1d7d8f575  status PROPOSED / NOT ACCEPTED
criteria       17 extracted
  DEMONSTRABLE               11
  PARTIAL                    3
  NOT_DEMONSTRATED           1
  NEEDS_ENGAGEMENT_EVIDENCE  2
  UNMAPPED                   0
deliverables   20 extracted
  DEMONSTRABLE               14
  PARTIAL                    2
  NOT_DEMONSTRATED           3
  NEEDS_ENGAGEMENT_EVIDENCE  1

sample packet  9 files included, 3 excluded for not passing
written to     output/
```

```
----------------------------------------------------------------------
Ran 26 tests in 0.671s

OK
```

## The split, and why the failures are the valuable part

| Status | Meaning |
|---|---|
| `DEMONSTRABLE` | A check ran against a real artifact and passed; the observed value is recorded. |
| `PARTIAL` | Part of the criterion is shown by an artifact, part is not. |
| `NOT_DEMONSTRATED` | A check ran and **failed**. The artifact exists and does not meet the criterion. |
| `NEEDS_ENGAGEMENT_EVIDENCE` | No file in this repository can demonstrate it. It needs a prime, a review window, or real University evidence. |
| `UNMAPPED` | No binding, or the bound artifacts are not on disk. |

Three findings worth reading:

**`AC-5.1.3` is `NOT_DEMONSTRATED`, and that is a real result.** No single delivered
source register carries all six required concepts. The rehearsal register has content
digests and currentness but **no custodian/owner and no authorization/provenance
column**; the workshare's synthetic evidence register has `enumerator_authority` but
**no content digest column**. Between them the concepts are covered; neither alone
satisfies the criterion. That is an actionable schema gap, not a score.

**`AC-5.2.6` and `AC-5.3.4` are `NEEDS_ENGAGEMENT_EVIDENCE`, permanently, until there is
a prime.** One asks whether prime review comments were incorporated; the other whether
nonconformances found during acceptance review were cured. No repository artifact can
evidence either, because no review has happened. A test asserts these two are never
marked `DEMONSTRABLE` and that every such criterion names its missing input.

**`AC-5.3.1` and `AC-5.3.6` are `PARTIAL` because there is only one generation.** "What
changed from draft" needs a draft and a final. Reported, not glossed.

## Two false results this build produced, and how they were caught

Reported because a check that lies in the *optimistic* direction and one that lies in
the *pessimistic* direction are equally useless.

1. **A false failure.** The first run reported the UIOWA-091 coverage matrix as covering
   9 of 12 cells. It covers all 12 — that lane labels the deployment area
   `deployment_operations` and the check spec said `deployment`. The check encoded the
   wrong vocabulary and manufactured a gap in another seat's work. Corrected against the
   actual column values. Same class of error as a false pass.
2. **A false violation.** The forbidden-representation guard flagged the rendered index
   for containing "the University accepted" — which appears only inside criterion
   5.3.5's own wording, *prohibiting* it. Quoting a rule is not breaking it. The guard
   now scans `authored_prose()` — the banner, derived statuses, check labels and
   observed values — and not the exhibit text the document is required to reproduce.
   Two further tests keep that narrowing honest: one poisons an authored field and
   asserts the guard still fires, another asserts the quoted criterion text is still
   present in the rendered output.

## Checked sample delivery packet

`output/sample_packet/` holds copies of the artifacts whose checks actually **passed**,
each with its sha256 and the criterion it answers, in `MANIFEST.json`. Artifacts bound
to a criterion whose check did **not** pass are listed under
`excluded_because_the_check_did_not_pass` with the observed reason — excluded, not
dropped. A test asserts every included file traces to a passing check and that the
exclusion list is non-empty.

## Files

| Path | What it is |
|---|---|
| `exhibit_parser.py` | Extracts criteria and deliverable items from the live exhibit and records its sha256, so drift is visible. |
| `checks.py` | Nine content-check kinds. Each returns PASS / FAIL / **UNAVAILABLE** — "could not look" is never collapsed into "looked and found it wanting". |
| `acceptance_map.json` | The bindings: criterion → checks, or criterion → named missing engagement inputs. |
| `build_index.py` | Runs the checks, derives status, renders the index, assembles the packet. |
| `test_acceptance_map.py` | 26 tests, including hostile and read-only proofs. |
| `output/` | The committed run against the lanes as they stood at build time. |

## Working vs. draft

**Working and tested:** the parser, all nine check kinds, status derivation, the index
and packet exports, the read-only guarantee, and the forbidden-representation guard.

**Draft / deliberately narrow:**
- The bindings cover the lanes present when this was built. Lanes are landing every few
  minutes; a criterion bound to an artifact that later moves reports `UNMAPPED` rather
  than silently passing, but the map will need re-pointing.
- Several criteria are bound to one lane's artifacts where more than one lane could
  serve. That is a binding choice, not a statement that other lanes fail.
- Deliverable items are bound more coarsely than acceptance criteria.

## University inputs still UNKNOWN

- Whether the prospective prime agrees with these bindings at all — **UNKNOWN**.
- The prime-owned half of the dependency list — **UNKNOWN**.
- Real University records, interviews and review comments — **UNKNOWN**. Every fixture
  behind every `DEMONSTRABLE` result is synthetic.
- Whether the controlling RFQ, amendments or an executed agreement change these criteria
  — **UNKNOWN**; the exhibit says they supersede it wherever they differ.

## Out of scope by construction

No maturity score, rating, percentile, certification or compliance verdict, and no
individual performance assessment. §4.5 of the exhibit excludes recommending or
endorsing any specific commercial product or vendor; this package does not widen that
and names no product.
