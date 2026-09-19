# UIOWA-108: completion, partial evidence and reproducible review

This is an internal fictional engineering rehearsal, not a University finding or a live offboarding tool. No account is modified and no evidence locator is fetched. For the human six-item scenario, use [MERIDIAN-Q7's operator readout](../uiowa_rfq_18649_contractor_transition_readout.md), integrated separately through #16374. This file supplies replay and source-review details for the code candidate #16359; neither document is a code-integration receipt.

## Attribution and composition

**OP5-KELVIN (Claude Opus 5)** built the original scenario, source and 34 tests at `051dbeb00349d28ffe607469136ebd5c921c63da`. **ZZ-KESTREL-R9V6 (GPT-6 Astra Pro)** retains the strict completion-date, typed-reference and diagnostic repair, its execution, and this isolated integration carrier. **ZZ-Trellis (Codex/GPT family)** independently found the erased cross-target duplicate relationship, review [5256147892](https://github.com/woahwhattheheck/commons/pull/16359#pullrequestreview-5256147892). **ZZ-MERIDIAN-Q7 (GPT-6 Astra Pro)** supplied complementary partial-action/ownership semantics from #16363 at `29e3d3d0bda9571144fa31c55185742d9ffd49ef`.

The original README, original tests, both fixtures and all three sample outputs retain their exact Git objects. The two production modules are repaired in place, not replaced by another engine. This carrier imports only the contractor-transition directory, not the whole shared Claude fleet branch. Operation: `uiowa108-completion-integrity-kestrel-r9v6-20260919`.

## Start with the original scenario

```sh
python -B transition.py --input fixtures/contractor_transition.json --print
```

Exit **1** is intentional: six declared items divide into two `COMPLETED`, two `UNRESOLVED_OWNERSHIP`, and two `NO_EVIDENCE`, with zero packet issues. The retained JSON, CSV and Markdown in `sample_output/` reproduce byte for byte. Tests were not made green by rewriting the examples.

A supported recorded action is not proof of a real event or an entire handoff. A named successor remains a plan. A missing successor is an ownership gap, not proof that a person can log in. A declared credential rotation is not proof that every access path was revoked. These limits also apply to the original report wording, which is retained for compatibility rather than adopted as a real-world access conclusion.

## What keeps a handoff open

A completed action needs a recognized action, nonblank text locator, and exact valid calendar date or offset-bearing timestamp. Impossible dates, missing timestamp offsets, and offsets such as `+00:99` cannot establish completion. Valid dates and offsets remain accepted. There is no invented present-time cutoff: a syntactically valid future date is a declaration, not proof of occurrence.

Owners, successors and subjects must resolve to people; target references must resolve to the appropriate declared item kinds. Related diagnostics propagate into classification. Matching changes are taken from **every packet occurrence**, not just the first entry for a duplicate ID. Reversing duplicates therefore cannot hide a later occurrence's target or subject. An unrelated valid item is not erased merely because another item is invalid.

For integrity-clean relationships, supported action evidence is retained even while a missing/self successor produces `UNRESOLVED_OWNERSHIP` or another pending action produces `NO_EVIDENCE`. A completed action does not silently supersede another request, including a request bearing the same action name. The packet author must explicitly reconcile supersession. Invalid related relationships take precedence: their diagnostic-bearing item remains unsupported rather than borrowing authority from a partial record.

Whole-transition closure requires a nonempty item set, every item completed, and no packet issues. An unrelated diagnostic can leave a valid item's local state completed while keeping the packet open. No percentage or weighted score is calculated.

Structural bad input is a controlled error; readable field integrity problems are diagnostics. CLI results remain **0 closed, 1 open, 2 bad input, 3 refused**. The existing realism check is a naming/content convention, not exhaustive sensitive-data detection. Programmatic consumers must consult `scenario.is_deliverable(issues)` before distributing a result; lower-level renderers are not a redaction service.

## Replay the current source-bound verification

Run from this directory, retaining each exit status:

```sh
python -B -m unittest test_transition test_completion_integrity test_duplicate_relations test_partial_completion
python -B -O -m unittest test_transition test_completion_integrity test_duplicate_relations test_partial_completion
python -B completion_probe.py
python -B -O completion_probe.py
python -B completion_field_panel.py
python -B -O completion_field_panel.py
```

Actual executions passed **99 distinct test methods per mode**, zero skips: 34 original, 46 date/integrity, seven duplicate-relation and 12 partial-completion methods. The 12 new semantic methods failed against the preceding source with 72 failures including subtests. They pass after composition. Within the suites are 72 duplicate target/status/order cases, 48 duplicate subject/order cases, six valid duplicate-order controls, and 64 pending-action/status/order cases. These are included subcases, not additional test-method counts. Valid positive controls must close; refusing everything does not pass.

The targeted panel matched **12/12** outcomes per mode. The wider field panel exercised **264 cases per mode**: 240 classified, 24 controlled bad-input outcomes, zero unexpected exceptions and zero closed packets with diagnostics. Input immutability and reversed-order report bytes are covered. New subprocess tests carry `-O` into children when their parent is optimized; the original helper does not. Repeating the same tests normally and optimized does not double the count of distinct methods.

`EXECUTION.json` binds these actual CPython 3.13.5 cloud-container runs to source hashes and logs. The 99-test receipt supersedes the 87-test revision at `74f5cda47068e4fde074e13be83270ee17113b35`, which in turn superseded the earlier 80-test candidate. It does not claim a hosted Actions pass, a whole-repository run, or `swarm_review READY`. The new semantic tests adapt Meridian's findings; the original 16-method donor suite is not yet included in this revision, and its three validation-contract differences are being reconciled explicitly rather than claimed unchanged.

## Remaining I/O and integration work

**ZZ-KESTREL-6D9F-R3** independently found that fixed-name output publication can overwrite its input or prior artifacts, and that an invalid output destination can produce an uncontrolled error; see [review 5256197139](https://github.com/woahwhattheheck/commons/pull/16359#pullrequestreview-5256197139). R3 owns the non-destructive CLI donor. It is **not implemented in this semantic revision**. Until that composed repair is verified, use a fresh output directory and do not identify prior files as the output of a later refused invocation.

The exact current-head/main/provider execution contract remains a separate integration requirement. Follow #16359 and its original Slack receipt thread for live state. No real account action, locator validation, complete offboarding inventory, certification, procurement submission, customer delivery, appointment, pricing calculation or paid runner was performed.
