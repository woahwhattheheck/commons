# TT ONE LAB+ carrier semantic generation

This note closes the post-merge semantic-generation RED discovered against the first recovered carrier.

## What is frozen at import

`carrier.py` reads the retained `source_manifest.json` once, validates the code-owned source contract, and constructs one private semantic generation. The public `compile_packet()`, `verify_packet()`, `source_manifest_digest()`, and `example_owner_input()` functions are closures over that generation.

The generation captures, rather than late-resolving:

- the exact source-manifest SHA-256;
- the seven mandatory price-row names;
- the six-deliverable source topology check;
- evaluation weights summing to 100;
- the proposal deadline;
- the Ministry submission mailbox and subject;
- the clarification-route conflict and printed typo evidence;
- minimum experience, reference, and validity requirements;
- the complete all-false external-authority map;
- canonical JSON / SHA-256 functions;
- strict validators, datetime parsing, regexes, and collection/builtin callables used by compile/verify.

Rebinding module globals or helper-looking names after import therefore cannot make compile and verify agree on a forged buyer route, source digest, deadline, price roster, or authority map. `verify_packet()` closes over the same private generation directly; it does not call a late-bound public `compile_packet` symbol.

This is an in-process semantic-integrity boundary, not code-signing or hostile interpreter isolation. Replacing the public function object itself, mutating Python runtime internals, or executing arbitrary native code is outside this artifact's claim.

## Time semantics

`evaluated_at` is caller-supplied historical/replay input. Every compiled packet states:

- `evaluation_time_authority = CALLER_SUPPLIED_REPLAY_ONLY_NOT_CURRENT`
- `current_deadline_readiness_claimed = false`

The deadline comparison answers only: **what would this owner packet's blocker state be at the supplied replay instant under this frozen buyer/source generation?** It does not claim the supplied instant is the current process time and cannot authorize a present-day submission.

No process-clock/current-submission API is exposed by this carrier. Current decision-making still requires owner/provider review of live time, source amendments, qualification evidence, pricing, collision state, and outbound authority.

## Tests

The retained focused suite runs through `test_tt_one_lab_lims_consultant.py` in normal and `python -O` mode. In addition to the original qualification/commercial/source hostiles, it now poisons legacy semantic globals, buyer route, source digest, deadline, price roster, helper names, stdlib module globals, the public compiler symbol, and the exported error-class symbol. Compile/verify must retain the import-time generation or fail closed.

No new active GitHub Actions workflow is introduced.
