# Emergent master prompt — OneWriter

Build a polished production-style web application named **OneWriter** for a real business coordination problem: multi-agent teams can independently decide to contact the same external party, causing duplicate outbound touches. OneWriter must make exactly-one-writer ownership visible and auditable *before* any external provider mutation. It is a coordination/evidence app, **not** an email sender.

## Non-negotiable product behavior

Implement the exact state semantics from `state_machine.json` and synthetic story from `demo_events.json`:

- deterministic normalized collision key over organization × domain × route × purpose × opportunity;
- states `CLEAR`, `LEASED`, `SENT_DNR`, `DEAD_ROUTE`, `HUMAN_EVENT_REOPEN`, `HOLD`;
- one atomic bounded lease per collision key;
- loser of a concurrent lease attempt is denied and still receives an immutable receipt;
- explicit stale lease expiration only after recorded expiry, followed by safe recovery;
- only active lease holder can record provider `SENT`, `BOUNCE`, or release;
- provider evidence reference is mandatory;
- `SENT` means `SENT_DNR`, blocking another writer until a genuine evidenced `HUMAN_EVENT` reopens one bounded next action;
- `BOUNCE` means `DEAD_ROUTE`, explicitly not buyer rejection;
- append-only hash-chained transition receipts, including denied actions;
- operator HOLD fences acquisition;
- no admin/demo shortcut may violate these rules.

Use the backend/database transaction or atomic conditional-write facilities available in Emergent. Do not implement lease safety as "read in browser, then write later."

## UX

Create a premium B2B operations UI, desktop-first but responsive:

1. **Control Room** — metric cards for active leases, collisions prevented, duplicate touches prevented, stale lanes recovered, route failures, human reopens. Live lane table with risk-state badges, search, filters, holder, expiry countdown.
2. **Propose Lane** — readable form, live normalized identity preview, collision-key prefix, existing-lane warning.
3. **Lane Detail** — state, allowed next actions, holder/expiry, evidence refs, full receipt timeline.
4. **Collision Demo** — side-by-side Agent Alpha vs Agent Beta claim attempt with a decisive single winner and denied second writer.
5. **Receipt Inspector** — recompute hash chain; include a local demo-only tamper preview that proves verification would fail without changing canonical history.
6. **Demo Runner** — reset synthetic fixture, run next event, run all, advance through stale expiry, export JSON.

Prefer a restrained high-contrast operations aesthetic: strong typography, dense but readable evidence tables, clear state badges, subtle transition motion, accessible keyboard/focus states, no gimmicky AI gradients, no fake charts.

## Synthetic data/privacy

Use only bundled synthetic companies and `.example` routes from `demo_events.json`. Do not invent real customer names, replies, payments, results, prize status, or impact metrics. Do not collect private buyer data for the public demo.

## Evidence and export

Every accepted or denied event should produce a receipt with:
`seq`, `event_id`, `at`, `actor`, `collision_key`, `action`, `accepted`, `prior_state`, `next_state`, `reason`, `prior_digest`, `digest`.

Canonical JSON serialization must be deterministic. Provide an Export Demo JSON action that outputs lane state, metrics, and receipt chain for comparison with the offline acceptance contract.

## Safety/authority copy in UI

Always display: **"OneWriter coordinates authority; it does not send external messages."**

No button may send email, submit a web form, send a DM, purchase anything, enter a contest, or mutate any external provider. No real credentials. No hidden webhook that can publish externally.

## Business-impact presentation

Add an Impact Evidence section showing measurable fields, not invented results:
- outbound intents observed;
- collision attempts;
- collisions prevented;
- duplicate touches prevented after provider-SENT;
- stale leases recovered;
- route failures correctly distinguished from human outcomes;
- median arbitration time, only once measured from real accepted timestamps.

Mark unmeasured fields `NOT YET MEASURED` until operational evidence is imported by an authorized owner.

## Build completion

Ship a working deployed app with the synthetic demo preloaded. Exercise all required flows yourself. Fix runtime/build errors. Return the deployed URL and concise build notes. Deployment alone is **not** authorization to submit the app to the contest or contact anyone externally.
