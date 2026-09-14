# QuietOps architecture

## Control plane

QuietOps treats model output as a **proposal**, never as authority. Three Strands roles are composed:

1. **EvidenceAuditor** — checks whether the normalized item is complete and whether ambiguity/currentness signals are present.
2. **RoutineWorkPlanner** — chooses a bounded way to finish routine work.
3. **AuthorityExplainer** — translates the deterministic gate result into a concise human-facing explanation.

The root `QuietOps` Strands Agent can invoke all three. Before any Agent is constructed, the application canonicalizes and detaches exactly one work-item generation. All authority-bearing `@tool` functions are closures over that bound snapshot and accept no replacement item argument. Crucially, the execution tool calls `core.process_offline()`, which calls `core.decide()` again. Prompt injection therefore cannot rewrite `kind`/evidence and turn `CONTACT_CUSTOMER`, `MOVE_MONEY`, `PRICE_COMMITMENT`, `LEGAL_INTERPRETATION`, `CONTRACT_ACCEPTANCE`, or generic `EXTERNAL_MUTATION` into autonomous work.

## Evidence generation and replay

Each evidence reference is `(ref, sha256)`. A ref cannot name two generations in one item. Evidence rows are sorted before the input generation is hashed, so harmless enumeration-order changes cannot remint an operation. Exact queue replays collapse; reuse of one `event_id` for a different content-bound operation fails closed. The normalized input, sorted evidence set, operation, and receipt are independently SHA-256 bound. Public receipt minting and verification recompute `decide(raw_item)` themselves rather than trusting a caller-supplied Decision object. A changed event id, input generation, result, or receipt field invalidates verification.

## Why deterministic receipts matter

Background agents are hard to trust when their only proof is prose. QuietOps receipts make a narrow claim: *this exact reversible action was evaluated from this exact evidence generation under this exact authority decision and returned this exact result.* They make no claim that a customer was contacted, money moved, or revenue earned.

## Optional AgentCore deployment

The hackathon does not require AgentCore, but AWS explicitly says it can strengthen Technical Implementation. A production deployment can package `quietops.strands_app:build_agents` inside an AgentCore runtime and use AgentCore Memory for durable session context. The authority core should remain local and deterministic; memory may supply context but must never widen authority.

Recommended production split:

- AgentCore Runtime: Strands orchestration and model provider.
- AgentCore Memory: prior normalized work/decision context only.
- Immutable evidence store: source snapshots and content hashes.
- QuietOps gate: local process library, no network dependency.
- External connectors: downstream of the gate and disabled for `HUMAN_DECISION_REQUIRED`.

## Threat model

Pinned hostiles cover:

- evidence aliasing and same-ref/different-generation splice;
- result and input replay/tampering;
- duplicate JSON keys and non-finite constants;
- binary float money paths;
- unsafe prototype-like keys;
- unknown action kinds;
- low confidence and explicit ambiguity;
- money-bearing items and external effects;
- human-required decisions attempting to mint execution receipts.

The v1 demo is intentionally not a provider-side exactly-once send/payment primitive. It demonstrates the safer boundary: those operations are escalated before any connector can be invoked.

## Outcome escalation

Authority applies both before and after reversible work. `RECONCILE_RECORDS` may run autonomously, but a non-zero variance deterministically produces a `RECONCILIATION_VARIANCE_DECISION` follow-up card while retaining the receipt for the completed analysis. The model is not responsible for noticing a magic status string.
