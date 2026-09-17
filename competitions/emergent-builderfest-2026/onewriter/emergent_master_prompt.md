# Emergent master prompt — OneWriter

Build a polished production-style web application named **OneWriter** for a real business coordination problem: multi-agent teams can independently decide to contact the same external party, causing duplicate outbound touches. OneWriter must make exactly-one-writer ownership visible and auditable *before* any external provider mutation. It is a coordination/evidence app, **not** an email sender.

Use `state_machine.json`, `demo_events.json`, `product_spec.md`, and `acceptance.py` as the semantic source of truth. Do not weaken their denial rules to make the demo easier.

## Non-negotiable authority architecture

The browser is not the authority.

- Authenticate users in the backend and derive `actor` and `role` there.
- Stamp canonical UTC event time in the backend. Never accept client-supplied role or authoritative `at` for state decisions.
- Reserve `SYSTEM` expiry for a backend system identity and `OPERATOR` hold for an authorized operator.
- Treat provider/human evidence references as evidence inputs that require authenticated adapters before real operational use. The public demo uses synthetic references only.
- Write event, state transition, metrics, and receipt atomically in one backend transaction.
- Enforce a unique event ID and a unique canonical collision-key row.
- Use database compare-and-set/transaction semantics for acquisition. A browser read followed by a later write is not sufficient.
- Hash-chain integrity is a mutation detector, not a signature and not provider authentication. Say so in the UI.

## Non-negotiable product behavior

Implement the exact v2 state semantics:

- deterministic canonical collision key over exactly organization × domain × route × purpose × opportunity;
- NFKC/case-fold/whitespace normalization with rejection of controls, format characters, line separators, and unsupported identity fields;
- states `CLEAR`, `LEASED`, `SENT_DNR`, `DEAD_ROUTE`, `HUMAN_EVENT_REOPEN`, `HOLD`;
- one atomic bounded lease per collision key;
- lease duration integer 1–3600 seconds;
- loser of a concurrent lease attempt is denied and still receives an immutable receipt;
- an expired holder cannot release or record SENT/BOUNCE;
- an expired lane cannot be reacquired until the backend `SYSTEM` performs explicit recovery;
- system expiry only at or after recorded expiry;
- a lease records `lease_return_state`; a lease acquired from `HUMAN_EVENT_REOPEN` returns there on release/expiry rather than becoming unrestricted `CLEAR`;
- only the active unexpired holder can record provider `SENT`, `BOUNCE`, or release;
- provider evidence reference is mandatory;
- `SENT` means `SENT_DNR`, blocking another writer until a genuine evidenced `HUMAN_EVENT` from `HUMAN_SOURCE` reopens one bounded next action;
- `BOUNCE` means `DEAD_ROUTE`, explicitly not buyer rejection;
- only `OPERATOR` may place HOLD;
- event time cannot move backward;
- append-only event-digest + receipt-digest chaining for accepted and denied semantic events;
- no admin/demo shortcut may violate these rules.

## Receipt contract

Every accepted or denied semantic event must produce a receipt with:

`seq`, `event_id`, `at`, `actor`, `role`, `collision_key`, `action`, `accepted`, `prior_state`, `next_state`, `reason`, `decision_input`, `event_digest`, `prior_digest`, `digest`.

`decision_input` must retain the normalized five-field lane plus `lease_seconds`, `provider_receipt`, and `human_event_ref` (using null where absent). Reject unknown event fields instead of silently dropping them from the authority record.

Canonical JSON serialization must be deterministic and finite. Verification must recompute both `event_digest` and the chain digest. A local tamper demo may alter a copy only.

## UX

Create a premium B2B operations UI, desktop-first but responsive:

1. **Control Room** — metric cards for active leases, collisions prevented, duplicate touches prevented, stale lanes recovered, route failures, human reopens. Live lane table with risk-state badges, search, filters, holder, expiry countdown, and return state.
2. **Propose Lane** — readable exact-five-field form, normalized identity preview, collision-key prefix, existing-lane warning.
3. **Lane Detail** — state, allowed next actions, authenticated role, holder/expiry, return state, evidence refs, full receipt timeline.
4. **Collision Demo** — issue two simultaneous backend acquisition requests. Show one decisive winner and one denied second writer; do not fake concurrency with sequential browser flags.
5. **Receipt Inspector** — recompute event and receipt hashes; include a local demo-only tamper preview that proves verification failure without changing canonical history.
6. **Demo Runner** — reset synthetic fixture, run next event, run all, invoke backend stale recovery, export JSON.
7. **Authority Boundary** — plainly distinguish authenticated backend facts, synthetic demo references, hash-chain integrity, and external provider truth.

Prefer a restrained high-contrast operations aesthetic: strong typography, dense but readable evidence tables, clear state badges, subtle transition motion, accessible keyboard/focus states, no gimmicky AI gradients, no fake charts.

## Synthetic data/privacy

Use only bundled synthetic companies and `.example` routes from `demo_events.json`. Do not invent real customer names, replies, payments, results, prize status, or impact metrics. Do not collect private buyer data for the public demo.

## Verification before completion

- Import the bundled v2 fixture and reproduce its exact metrics/final states.
- Exercise a real concurrent backend acquisition race repeatedly and prove exactly one winner.
- Exercise wrong-role expiry, early expiry, expired-holder SENT/BOUNCE/release, duplicate event ID, backward time, invisible identity, missing evidence, reopen release/expiry, and receipt tamper hostiles.
- Compare exported receipt bytes/semantics with the offline acceptance contract.
- Confirm no client request can select `SYSTEM`, `OPERATOR`, or authoritative time.
- Confirm no route sends anything externally.

## Safety/authority copy in UI

Always display:

> **OneWriter coordinates authority; it does not send external messages. Backend-authenticated roles and time govern decisions; receipt hashes prove retained-byte integrity, not external provider truth.**

No button may send email, submit a web form, send a DM, purchase anything, enter a contest, or mutate any external provider. No real credentials. No hidden webhook that can publish externally.

## Business-impact presentation

Add an Impact Evidence section showing measurable fields, not invented results:

- outbound intents observed;
- collision attempts;
- collisions prevented;
- duplicate touches prevented after provider-SENT;
- stale leases recovered;
- route failures correctly distinguished from human outcomes;
- median arbitration time, only once measured from backend-accepted timestamps.

Mark unmeasured fields `NOT YET MEASURED` until operational evidence is imported by an authorized owner.

## Build completion

Ship a working deployed app with the synthetic demo preloaded. Exercise all required flows yourself. Fix runtime/build errors. Return the deployed URL and concise build notes. Deployment alone is **not** authorization to submit the app to the contest, contact anyone externally, import private lead data, or replace the team's live Muse/outbound controls.
