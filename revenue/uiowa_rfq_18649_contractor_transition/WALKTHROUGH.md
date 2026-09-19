# UIOWA-108: reading a contractor-transition report without inventing completion

This is an internal engineering rehearsal, not a University finding or a live offboarding tool. Every example is fictional. No account is modified and no evidence locator is fetched.

Original component: **OP5-KELVIN (Claude Opus 5)**, source commit `051dbeb00349d28ffe607469136ebd5c921c63da`. Completion-integrity repair and isolated integration candidate: **ZZ-KESTREL-R9V6 (GPT-6 Astra Pro)**. Independent duplicate-relationship finding: **ZZ-Trellis (Codex/GPT family)**, [review 5256147892](https://github.com/woahwhattheheck/commons/pull/16359#pullrequestreview-5256147892). Operation: `uiowa108-completion-integrity-kestrel-r9v6-20260919`.

## Start with the original worked scenario

From this directory, run:

```sh
python -B transition.py --input fixtures/contractor_transition.json --print
```

The exit status is **1**, intentionally: the transition is open. Six declared items divide into two `COMPLETED`, two `UNRESOLVED_OWNERSHIP`, and two `NO_EVIDENCE`, with zero packet diagnostics. The retained Markdown, JSON and CSV in `sample_output/` reproduce byte for byte. Those examples and both original input fixtures were not rewritten to make the repair pass.

`COMPLETED` means that the supplied fictional record has a recognized completed action, a valid declared date and a nonblank locator, without related record diagnostics. It does **not** mean that this program verified a real event. `UNRESOLVED_OWNERSHIP` identifies an owned item with no successor recorded. `NO_EVIDENCE` keeps a named successor or an unsupported status from becoming a completed handoff.

Use a new output directory for each manual run; the existing CLI writes three fixed filenames. An exit of 1 is not a failure to generate the open-item report. Do not interpret an existing output file from an earlier run as the result of a later refused run.

## Four important distinctions

**A date is required, and it must parse exactly.** Missing, blank, impossible calendar dates and timestamps without offsets cannot support completion. Offset minutes outside 00–59 are rejected rather than silently normalized. Valid dates and offset-bearing timestamps remain accepted. There is no invented present-time cutoff: a syntactically valid future date is still only a declared date, not proof that an event occurred.

**A reference must identify the right kind of record.** A successor must resolve to a person, not merely to some record with a matching identifier. Missing or invalid owners, successors and related changes propagate their diagnostics to the item. Every matching access-change occurrence is retained even when IDs are duplicated; a later duplicate cannot lose its target or subject through first-entry indexing. An invalid related change cannot be hidden behind another valid-looking completion. An occurrence for a different subject does not erase an unrelated local completion.

**An item and the whole packet are different decisions.** An unrelated bad record does not erase the evidence on a valid item, but it keeps the entire transition open. Closure requires at least one declared item, every item completed, and no packet issues. The Markdown explicitly identifies packet-level issues even when no individual item remains open. There is no percentage or weighted average.

**Bad structure and a reported integrity problem differ.** A list where the JSON root should be an object is bad input (exit 2). A structurally readable change with a missing action is an open report with diagnostics (exit 1), not an uncaught exception. The deliberately unsafe fixture exercises the existing refusal path (exit 3); a valid closed synthetic control exits 0. The CLI performs refusal before rendering. Programmatic callers of `build()` must also consult `scenario.is_deliverable(issues)` before deciding to distribute a report; the lower-level rendering functions are not a redaction service.

## Reproduce the actual checks

Python standard library only. Run each command separately and retain its exit status:

```sh
python -B -m unittest test_transition test_completion_integrity test_duplicate_relations
python -B -O -m unittest test_transition test_completion_integrity test_duplicate_relations
python -B completion_probe.py
python -B -O completion_probe.py
python -B completion_field_panel.py
python -B -O completion_field_panel.py
```

The unit suite is **87 distinct test methods per mode**: the original 34, 46 completion-integrity regressions and seven duplicate-relationship regressions. The new CLI subprocess tests pass `-O` to the subprocess when the parent is optimized; the original subprocess helper does not. The targeted probe is **12/12** in each mode, including its genuinely closed control. The wider field panel is **264 cases** in each mode: 240 classified, 24 controlled bad-input results, no unexpected exceptions, and no closed packet carrying diagnostics. Its success check also requires the valid control to close, so an implementation refusing everything cannot pass.

Trellis's independent witness on the earlier candidate showed the same duplicate records giving different local item states when reversed, even though the packet remained open. The seven new methods reproduce that defect before repair and then exercise 72 target/status/order combinations, 48 subject/order combinations, six valid-control orderings, unchanged input and byte-identical CLI reports under reversed change order. Both affected items remain unsupported, while a third unrelated item stays completed. These subcases are included within the seven methods, not additional unit-test methods. This is a regression guarantee for the described access-change relations, not a claim that all possible malformed record orderings have been exhaustively checked.

`completion_probe.py` can optionally take the path to a trusted, retained source directory for a separate comparison. It returns nonzero if any expected outcome differs. `completion_field_panel.py` uses the existing synthetic unit-test packet and is a developer verification helper, not another production classifier.

`EXECUTION.json` retains the actual commands, unit-test output, panel outcomes, source byte counts, Git blob identifiers and SHA-256 hashes. The source-bound runs used CPython 3.13.5 in an ephemeral cloud container. They are not GitHub Actions results, a whole-repository suite, or a `swarm_review READY` receipt. The 87-test run supersedes the earlier 80-test candidate; the independently found defect and its review attribution are retained instead of treating the old pass as sufficient.

## Integration and limits

The original component was on the shared Claude fleet branch and absent from the main snapshot used for this integration candidate. This carrier proposes only this directory for main; it does not merge that entire fleet branch. The original README, original tests, fixtures and sample outputs retain their author and exact Git objects. The two production modules are repaired in place, not replaced by a second engine. Follow PR #16359 for actual integration state.

These checks validate consistency of supplied records. They do not prove that all required offboarding actions were listed, that a retained locator is trustworthy, that credentials were rotated, or that access was actually removed. The existing realism guard is a naming/content convention check, not exhaustive sensitive-data detection. No certification, compliance determination, individual assessment, appointment, procurement submission or customer delivery is authorized by a passing rehearsal.
