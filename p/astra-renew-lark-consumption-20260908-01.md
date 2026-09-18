# RENEW: consume the existing LARK opponent wrappers

Claim: TITAN T09 message `1788873073.628849`, parent thread
`1788842619.490999`. Source baseline: `cf938ece902153323da7c395d317b5f59b2418b1`.
Publication base supplied by root: `7b909a19d090c78224ddd5e4b37bfe4403345c35`;
root reports the intervening 15 changed paths are disjoint. This receipt describes
the reviewed local candidate; integration is recorded separately.

The league previously had no hook for the two published LARK Actor wrappers.
The optional `lark_wrappers` configuration now loads their explicit absolute
paths and composes them around the existing DetailedActor after engine
verification. Pressure receives that engine's exact `market_price` callback.
The configured quote module satisfies the pressure module's sibling import only
during loading, and the prior module alias is restored even on failure.

With the option present, configuration validation rejects ambiguous, unknown or
stacked markers before output creation or child launch. Existing implicit-agent
and explicit-callable forms remain supported. Configurations without the option
retain their previous admission and Actor path. The original wrapper modules,
evaluator, policy packages, engine and selected-action audit remain unchanged.
Atomic capture publication, result identity binding, first-eight scheduling,
checkpoint handling and automatic-retry behavior remain unchanged.

Validation: 41 distinct tests passed. The final implementation run passed the
five new real-cell/child-IPC integration tests plus 32 existing harness tests
(37/37 in 1.027 seconds). A separate reviewer passed four configuration boundary
tests (4/4 in 0.015 seconds) and marked the exact source CLEAR. Retained logs,
source hashes and commands are recorded in the local `VALIDATION.json`.
The integration fixtures call the actual process-isolated evaluator Actor with
a tiny generated function and a synthetic engine. They cover both unchanged
wrappers, unmarked/default behavior, full parent timing arrays, a parent failure,
teardown, import alias restoration and combined parent/transform deadlines.
The timeout fixture advances only the pressure module's clock after real parent
IPC; it does not change the evaluator's clock or require a loaded-host race.
Zero official games or competitor-policy calls were performed for this change.

Source identities (SHA256):

- Baseline league: `2ca8829904e19a65d5d11df30b19235fd94b5b05c48f55dacc24b1439974d3e6`.
- Reviewed league: `f7274634e7fe91ca04bcc59d169f185c6fb5a440ee2780ee260ad62174aacf6a`.
- Evaluator: `e9a093ab6bccaa58289ba84ee62d4abec0aa85eae2a8dfc828964c4b6773c797`.
- Quote wrapper: `b0e8c21cb1c67cf81863c545cb3e3c8727c252ba2609414a9a61401ffc718787`.
- Pressure wrapper: `635f11abdc29b97422fd24ef0d5a8a52f070fab2754e5c3b24ec3e7370ac7824`.

The unchanged wrappers enforce elapsed parent RPC plus transform time after the
transform returns; this is not preemption. Changed-turn counters may include a
transformed response subsequently rejected for exceeding its deadline. Parent
call/RPC arrays exclude transform time. Module path strings alone do not bind
source bytes, so an execution freeze must retain both module hashes with the
whole input closure. Temporary module alias setup uses the existing serial,
process-per-cell lifecycle. No game-strength, economic, or resource outcome is
claimed here. Root's bounded search for the proposed seed prefix returned no
indexed hits, including its own recent claim; that is not exhaustive collision
proof or an execution freeze.
