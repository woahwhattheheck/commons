# Builder Fest submission copy — DRAFT_NOT_SUBMITTED

> **Do not submit this text as-is.** Replace bracketed evidence placeholders only with measured, retained business-use facts.

## Title

OneWriter — stop duplicate outreach before it hits a hot lead

## One-line description

An atomic coordination desk for multi-agent teams: one writer gets the lease, duplicate claimants are stopped, provider outcomes stay truthful, and every transition is auditable.

## Problem

Our business uses multiple AI/operator sessions in parallel. That creates a nasty coordination failure: two workers can independently discover the same high-value lead and decide to contact it seconds apart. A normal task board does not solve the race. Duplicate outreach looks like spam and can damage the opportunity.

## What OneWriter does

Every planned external touch is normalized into one collision key: organization × domain × route × purpose × opportunity. Workers claim an expiring lease before acting. Only one live writer can hold the lane.

OneWriter also keeps outcome semantics honest:
- provider SENT creates a hard do-not-repeat fence;
- a bounce is a dead route, not buyer rejection;
- stale leases can be recovered;
- only retained human evidence reopens a bounded next action;
- every transition produces an immutable receipt.

The app coordinates. It never sends the message itself.

## Real business use

`[REQUIRED BEFORE SUBMISSION: measured use window]`

`[REQUIRED: number of real workers/agents using the app]`

`[REQUIRED: collisions prevented and denominator/population]`

`[OPTIONAL IF MEASURED: stale lanes recovered, route failures separated, time-to-lease]`

No synthetic-demo number belongs in this section.

## Why it can scale

The same single-writer race appears anywhere several people or agents can act on one external target: sales, partnerships, recruiting, vendor follow-up, support escalation, approvals, and account operations. OneWriter's collision key, atomic lease, typed outcome states, and receipt log are workflow primitives rather than a one-off CRM feature.

## Emergent build

`[REQUIRED: describe the actual Emergent build choices used in the deployed app—database, atomic lease mechanism, UI screens, deployment iteration, and any Emergent-native features. Do not invent.]`

## Demo flow

1. Two agents claim the same synthetic hot lead three seconds apart.
2. One gets `GRANTED`; the other gets `DENIED_ACTIVE_LEASE`.
3. The winning writer records a provider SENT receipt; the lane becomes `HARD_DNR`.
4. Another claim is blocked.
5. A retained human-event receipt reopens exactly one next action.
6. A second synthetic lane shows stale-lease recovery and a 550-style route failure becoming `DEAD_ROUTE`, not rejection.
7. The dashboard recomputes the receipt-backed metrics live.

## Evidence / privacy

The public demo uses synthetic organizations and `.invalid` routes. Private buyer content is not exposed. Real-use contest claims are aggregate and receipt-backed.

## Submission-state checklist

- [ ] working Emergent app deployed
- [ ] used in the real business
- [ ] measured impact packet complete
- [ ] privacy review complete
- [ ] no other active team/participant submission conflicts
- [ ] final title/description checked
- [ ] submission action intentionally performed
- [ ] confirmation email received
- [ ] platform status reads Submitted

Until all boxes through actual submission are complete, state is `DRAFT_NOT_SUBMITTED`.
