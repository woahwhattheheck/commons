# OneWriter — Emergent Builders' Fest 2026 source packet

Status: **SOURCE_PACKET / NOT SUBMITTED / NOT DEPLOYED**  
Carrier: `woahwhattheheck/commons#15421`  
Operation: `EMERGENT-BUILDERFEST-ONEWRITER-ZSOL-20260917`

## What it solves

Multi-agent sales and operations teams can independently decide to contact the same external party within seconds. The failure is not merely duplicated labor: two outbound messages can confuse a hot lead, make the team look automated or disorganized, and destroy otherwise good commercial intent.

**OneWriter** is a coordination and evidence application that turns an outbound intention into an auditable single-writer decision *before* any email, form submission, DM, or other provider mutation. It never sends the message itself. It decides whether exactly one worker may proceed and records what happened afterward.

The product is grounded in a real Token Junkie Labs operating requirement. Public competition demos must use only the synthetic `.example` identities in this packet; no private lead data is required.

## Authority boundary

The Python engine is a deterministic offline contract, not an identity, clock, or provider-authentication service.

- Bundled roles, timestamps, and evidence references are trusted **synthetic** fixture facts.
- A deployed backend must authenticate actor/role, stamp UTC time, bind provider/human evidence through authenticated adapters, and commit state plus receipt atomically.
- A client cannot choose `SYSTEM`, `OPERATOR`, or authoritative time.
- Hash chaining detects changes to retained bytes. It is not a signature and does not prove an external provider or human event.
- OneWriter does not replace the team's live Muse/outbound controls merely because it models the same problem.

## Demo story

1. `agent-alpha` proposes a synthetic Acme Fabrication lane and gets a 30-second lease.
2. `agent-beta` tries the same normalized lane one second later. OneWriter rejects the second writer and records a collision-prevention receipt.
3. Alpha goes stale. The backend system expires the lease at the recorded time; Beta safely recovers it and the recovery is measured.
4. Beta records a synthetic provider `SENT` reference. The lane becomes `SENT_DNR`; another acquisition attempt is denied as a duplicate-touch prevention.
5. A synthetic human-source event reopens one bounded next action. If that lease is released or expires, the lane returns to `HUMAN_EVENT_REOPEN`, not unrestricted `CLEAR`.
6. A second synthetic route receives a 550-style provider result. OneWriter records `DEAD_ROUTE`, explicitly *not* buyer rejection.
7. The dashboard shows state, live leases, prevented collisions, prevented duplicate touches, stale recoveries, route failures, human reopens, and the event-bound receipt chain.

Run the proof locally:

```bash
cd competitions/emergent-builderfest-2026/onewriter
python acceptance.py
python -m unittest -v test_acceptance.py
python -O -m unittest -v test_acceptance.py
```

All three commands must pass without network access or third-party Python packages. The root retained-CI bridge separately requires a positive test count in normal and optimized Python.

## Packet map

- `product_spec.md` — roles, authority boundary, state machine behavior, and acceptance criteria.
- `emergent_master_prompt.md` — one-shot build instruction for the Emergent browser executor.
- `state_machine.json` — machine-readable v2 state/role/receipt contract.
- `demo_events.json` — deterministic synthetic replay with expected results.
- `acceptance.py` — strict offline engine, decision-input receipt binding, replay verifier, CLI.
- `test_acceptance.py` — hostile role, time, collision, stale-lease, provider-truth, Unicode, and tamper tests.
- `impact_evidence.md` — safe before/after evidence plan; no invented impact numbers.
- `submission_copy.md` — draft-only public listing copy.
- `/test_onewriter_emergent_builderfest.py` — retained Commons bridge executing the full nested suite in normal and optimized Python.

## Security and truth properties retained by v2

- exact five-field canonical lane identity with NFKC/casefold normalization and invisible-character rejection;
- engine-level unique event IDs and monotonic time;
- action-to-role fencing;
- explicit system-only stale recovery;
- expired-holder fail-closure;
- reopen-origin preservation;
- evidence-bearing decision input inside every receipt;
- event digest plus receipt-chain digest;
- strict JSON duplicate-key/non-finite rejection;
- positive-count normal and optimized hostile execution.

The Python model is sequential and therefore does not prove a deployed database race. The Emergent implementation must use a real backend transaction/compare-and-set and separately demonstrate that simultaneous acquisitions yield exactly one winner.

## External authority boundary

This repository work does **not** authorize any Emergent account mutation, deployment, purchase, contest submission, public launch, buyer contact, email, DM, or form submission. A browser-capable executor must separately establish contest/account access, build the app in Emergent, deploy it, exercise backend concurrency and role/time controls, use it in the business with owner authorization, capture real evidence, re-census for a competing submission, and obtain the team's current single-writer publication authority before submitting.

## Contest fit

The product is designed around the contest's published scoring dimensions recorded in `#15421`: business impact/scale, problem solving, meaningful Emergent use, and UI/UX, while acknowledging that public upvotes are a separate distribution requirement. The source packet makes no claim that a deployment, submission, upvote, prize, ranking, customer outcome, or business impact has occurred.
