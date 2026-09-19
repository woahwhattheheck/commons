# UIOWA-080 — AI integration and portability readiness

Work order **UIOWA-080**. Built by seat **OP5-QUARRY** (Claude Opus 5).

An architecture assessment kit for putting AI capability into existing delivery
workflows: **three structurally different reference patterns**, an **integration
decision worksheet** that reads a fixed question set into a pattern fit, a
**portability model that produces a number instead of an adjective**, and a **worked
abstraction where swapping the provider requires zero changes to calling code**.

**Scope rule held throughout, and checked in code:** capabilities are described by
**capability class** and by architecture. No commercial product is named, compared,
or recommended for procurement anywhere in this lane.

---

## Run it

Python 3 standard library only. No installs. No network at runtime.

```bash
cd revenue/uiowa_rfq_18649_ai_integration

python3 build_kit.py                          # generate the whole kit into out/
python3 demo_swap.py                          # the provider-swap demonstration
python3 -m unittest -v test_ai_integration    # 46 tests
```

`build_kit.py` is deterministic — two runs produce byte-identical output, so a
reviewer can diff runs and see only what really changed. It exits non-zero if the
vendor-neutrality tripwire finds anything in the generated artifacts.

### Generated into `out/`

| File | What it is |
|---|---|
| `reference_patterns.md` | The three patterns compared on identical axes |
| `integration_decision_worksheet.md` | Per-workflow worksheet, answers, verdicts, unresolved evidence |
| `integration_decision_worksheet.csv` | Same verdicts, one row per workflow × pattern |
| `worksheet_evaluations.json` | Full machine-readable evaluation |
| `portability_blast_radius.md` | Provider-swap edit-point scoring with the method shown |
| `portability_scores.json` | Scores plus rejected (malformed) inventories |
| `swap_receipt.json` | Real run record of the swap demonstration |
| `neutrality_check.json` | Tripwire result over every generated text artifact |

---

## The three patterns

Structurally different, not three flavors of one thing.

| | **A** Synchronous in-request | **B** Asynchronous queued/batch | **C** Human-in-the-loop review |
|---|---|---|---|
| Shape | request → capability → response | submit → queue → worker → store → read | draft → review queue → person → effect |
| Interface surface | Smallest (1 call) | Medium (4 contracts) | Largest (+ decision record) |
| External data crossing | Per request, live record | Per item, out of band | Same as underlying transport |
| **Internal** staged copies | None created | Queue + result store + DLQ | + reviewer decision record |
| If capability is SLOW | User waits; pool-exhaustion risk | Backlog grows silently | Absorbed by the review queue |
| If capability is DOWN | Needs a degraded answer or the workflow is down too | Nothing lost if the queue is durable | Falls back to the unaided process — *if it still exists* |
| Availability coupling | HIGH | LOW (completion time still coupled) | LOW technically / HIGH organizationally |
| Binding constraint | Capability p99 latency | Throughput and rate limits | Reviewer capacity |
| Swap cost | Contained only if a port exists | Lowest; replayable validation | Code cheap, workflow expensive |
| First integration | 5–12 eng-days | 12–25 eng-days | 18–35 eng-days |

Three points in there are load-bearing and are easy to get backwards:

- **B has the largest *internal* data-governance surface**, not the smallest. The
  external boundary crossing is identical to A's, but B additionally creates staged
  copies in a queue, a result store and a dead-letter queue. The asynchronous pattern
  gets assumed to be the safer one because nobody is waiting.
- **C's binding constraint is reviewer capacity, not service uptime.** A capability
  twice as fast buys nothing if reviewers are saturated — and a saturated review queue
  becomes a rubber stamp, which is *worse* than no review because it manufactures the
  appearance of oversight.
- **C's fallback decays.** It degrades to the unaided process only while that process
  can still actually be executed. Inability to run it is an open finding, not a
  detail.

Every pattern carries a **deterministic baseline** to measure against, because a
benefit claim with no baseline is not a measurement.

---

## Portability, made countable

"We can swap providers later" is the most confidently asserted and least evidenced
claim in an AI integration plan. This kit refuses to take it as an adjective and
answers it two independent ways.

### 1. Score the declared code surface

`edit_points = sum(count × weight)` over eight surfaces. Weight > 1 marks a surface
that **propagates** — a vendor type or a unit convention drags its call sites with it.

Bands: `CONTAINED` 0–2 · `PARTIAL` 3–9 · `PERVASIVE` 10+ ·
`INSUFFICIENT_EVIDENCE` when any surface was not inventoried.

Real output on the fixtures:

```
HRI-INTAKE-01       39 edit points  PERVASIVE
HRI-ARCHIVE-02       2 edit points  CONTAINED
HRI-AWARD-03         6 edit points  INSUFFICIENT_EVIDENCE (FLOOR, incomplete inventory)
HRI-MALFORMED-99   NOT SCORED - surface counts must be non-negative integers or UNKNOWN
```

**An un-inventoried system scores 0 edit points and is *not* CONTAINED.** "We counted
nothing" and "there is nothing to count" are different facts, and conflating them is
exactly how a swap gets sold as cheap. A partial inventory reports its total as a
**FLOOR** and gets no band at all.

### 2. Demonstrate it, don't assert it

`portlib/` is a small working example. One domain-shaped port
(`ClassificationPort.classify(Document) -> Classification`), one caller
(`portlib/caller.py`) holding the actual workflow logic, and two **fictional**
providers with deliberately incompatible surfaces:

| | ALPHA (`hosted-inference-api`) | BETA (`self-operated-model`) |
|---|---|---|
| Response | flat `{"label","score","explain"}` | nested `{"result":{"category_name","confidence_pct","notes"}}` |
| Confidence unit | fraction 0.0–1.0 | percent 0–100 |
| Categories | domain names directly | upper-case provider taxonomy requiring a map |
| Errors | `AlphaTimeout`, `AlphaRefused` | `BetaUnavailable(retry_after)`, `BetaSlowLane` |

Real output from `python3 demo_swap.py`:

```
caller.py unchanged across every run  : True
distinct caller.py hashes observed    : 1
lines of calling code changed to swap : 0
scan portlib/caller.py                : independent=True, violations=0
scan portlib/caller_leaky.py (control): independent=False, violations=5
                                        (AlphaTimeout, _AlphaWireClient, fake_alpha)
```

The sha256 of the caller module is recorded on both sides of the swap and compared.
`portlib/caller_leaky.py` is a **deliberate negative control** — non-portable calling
code with four marked leaks — so the scanner is *known to have teeth*. A scan that has
never caught anything is not evidence.

### 3. …and the demonstration disproves its own headline

Same caller, same policy, healthy providers, same five documents:

```
provider ALPHA (healthy) : 3 auto-routed, 2 to human review
provider BETA  (healthy) : 2 auto-routed, 3 to human review
```

Zero lines changed and the auto-routing rate still moved 50% on that sample, because
BETA returns 66% confidence on an item ALPHA returns 84% on and the floor is 0.70.
**Code portability and behavior portability are different purchases, and only the
first one is cheap.** A provider swap is an adapter-sized *code* change and a
re-calibration-sized *workflow* change: any threshold derived from observed accept
rates has to be re-established before it is trusted again. That is the failure that
shows up two weeks after a "successful" cutover. `swap_receipt.json` records it as
`behavioral_delta_same_code_different_provider`.

---

## Failure behavior, exercised rather than described

All three degraded modes run for real in `demo_swap.py` and are asserted in the tests:

| Capability state | Port-level error | What the caller does |
|---|---|---|
| Slow | `ProviderTimeout` | All items → a person, marked `degraded`, failure class named |
| Unavailable | `ProviderUnavailable` (+ retry hint) | All items → a person, `degraded`, retry hint surfaced |
| Unusable answer | `ProviderContractViolation` | All items → a person, `degraded` — *not* a low-confidence guess |

**The degraded path never invents an answer.** An unreachable capability produces
UNKNOWN-equivalent handling, not a default category. Vendor exception types are
translated at the adapter wall, so no `except <vendor error>` ever appears in
workflow code — error-taxonomy coupling is the portability cost that gets discovered
during the first outage *after* the swap.

---

## Fictional fixtures

Everything in `data/workflows.json` is **FICTIONAL**. Harbor Ridge Institute does not
exist. There are **no University of Iowa data, findings, systems or measurements** in
this lane. Each fixture carries a real strength *and* a real gap:

| Workflow | Strength | Gap |
|---|---|---|
| `HRI-INTAKE-01` Intake triage | Pre-AI rule still runs and was measured on the same items, so a degraded answer genuinely exists | Built with no port; wire shape reaches six request handlers → `PERVASIVE` |
| `HRI-ARCHIVE-02` Archive backfill | Behind a port from day one; one worker touches the capability → `CONTAINED`, swap validatable by replay | Baseline never measured, so any benefit claim is unfalsifiable |
| `HRI-AWARD-03` Award narratives | Reviewer capacity was *measured*, on reviewing drafts rather than inferred | That measurement disqualifies the plan: peak 30/hr vs capacity 12/hr |
| `HRI-MALFORMED-99` | — | Deliberate hostile input; exists to prove malformed answers have observable handling |

The award workflow is the kit's sharpest output: **all three patterns come back
non-supportable**, with A disqualified on timing, C disqualified on measured review
capacity, and B `UNDETERMINED` pending one unanswered data question. That is the
correct answer, and it is more useful than a pattern recommendation would have been.

---

## What is real vs. draft

**Real and runnable now**

- The worksheet engine, its rule set, and every verdict path (46 passing tests).
- The portability scorer, its bands, its FLOOR handling, and its refusal to score a
  malformed inventory.
- The static independence scanner, with a negative control proving it fires.
- The port, both fictional adapters, conformance checking, and all three degraded paths.
- The vendor-neutrality tripwire, including its own false-positive test.
- Deterministic generation of all eight output artifacts.

**Draft / illustrative**

- The effort ranges in each pattern (5–12 / 12–25 / 18–35 engineer-days) are
  **planning placeholders**, not estimates of University work. They are stated as
  ranges because that is the honest precision available before scoping.
- The worksheet's rule thresholds (which answers disqualify which pattern) are a
  defensible first cut meant to be argued with. Every verdict names its question so a
  reviewer can contest the answer rather than the tool.
- The band boundaries (0–2 / 3–9 / 10+) are a judgement, not a measurement.

**Known limitation, stated rather than buried:** the vendor-neutrality check is a
**tripwire, not a proof**. It cannot show the absence of a product name, because it
carries no vendor list — shipping a denylist of real vendors into a client
deliverable would itself put product names in the deliverable. The substantive control
is the **closed capability vocabulary**: every capability reference must resolve to one
of six declared classes. The tripwire adds three structural tells (trademark marks,
versioned proper nouns, procurement phrasing) on top of that. Its own false-positive
test is in the suite — it caught the guard flagging `NIST AI RMF 1.0` as a product
name, which was a real defect and is fixed.

---

## University inputs still UNKNOWN

These are institution inputs this kit deliberately leaves blank. None of them is
defaulted, zeroed, or inferred:

1. Measured p50/p95/p99 of any candidate capability class under the institution's own
   payload sizes.
2. Current request timeouts and connection-pool limits on the services that would host
   a synchronous call.
3. Whether a **defined, exercised** degraded answer exists per candidate workflow — a
   fallback that has never been run under load is UNKNOWN, not a mitigation.
4. Whether durable queue infrastructure with an owned, monitored dead-letter path
   exists, and who operates it.
5. Acceptable completion-time commitment per workflow — must be stated by the workflow
   owner, not inferred from current runtimes.
6. Whether content may be staged into internal queues and result stores under its own
   handling terms.
7. Reviewer capacity in items per person-hour, **measured on reviewing drafts** —
   reviewing a draft and producing one are different tasks.
8. Who owns the auto-accept threshold. An unowned threshold moves informally.
9. Whether reviewer decision records may be retained and reused to tune a capability,
   and under whose consent.
10. Reprocessing budget when a capability version changes.
11. Whether the unaided path for each workflow can still be executed today.

---

## What this lane does not do

No real University findings, no live data, no network calls, no outreach, no
scheduling. No certification, compliance, maturity-score, or peer-percentile claims.
No individual performance scoring — every measurement here is about a *workflow* or a
*code surface*, never about a person. And no commercial product named, compared, or
recommended for procurement.

## File map

```
patterns.py            three reference patterns + capability vocabulary + neutrality guard
portability.py         swap blast-radius scoring + static independence scanner
worksheet.py           question set, fit rules, evaluation, Markdown/CSV rendering
unknowns.py            UNKNOWN sentinel with no arithmetic
build_kit.py           deterministic generator for everything in out/
demo_swap.py           the provider-swap demonstration and its receipt
portlib/port.py        domain types, the port, port-level errors, conformance check
portlib/caller.py      the calling code whose invariance IS the portability claim
portlib/caller_leaky.py  deliberate negative control — do not copy
portlib/providers/     fake_alpha.py, fake_beta.py — FICTIONAL adapters
data/workflows.json    FICTIONAL fixtures
test_ai_integration.py 46 unittest cases
```
