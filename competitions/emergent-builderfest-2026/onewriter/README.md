# OneWriter — Emergent Builders' Fest 2026 source packet

Status: **SOURCE_PACKET / NOT SUBMITTED / NOT DEPLOYED**  
Carrier: `woahwhattheheck/commons#15421`  
Operation: `EMERGENT-BUILDERFEST-ONEWRITER-ZSOL-20260917`

## What it solves

Multi-agent sales and operations teams can independently decide to contact the same external party within seconds. The failure is not merely duplicated labor: two outbound messages can confuse a hot lead, make the team look automated or disorganized, and destroy otherwise good commercial intent.

**OneWriter** is a coordination and evidence application that turns an outbound intention into an auditable single-writer decision *before* any email, form submission, DM, or other provider mutation. It never sends the message itself. It decides whether exactly one worker may proceed and records what happened afterward.

The product is grounded in a real Token Junkie Labs operating requirement. Public competition demos must use only the synthetic `.example` identities in this packet; no private lead data is required.

## Demo story

1. `agent-alpha` proposes a synthetic Acme Fabrication lane and gets a 30-second lease.
2. `agent-beta` tries the same normalized lane one second later. OneWriter rejects the second writer and records a collision-prevention receipt.
3. Alpha goes stale. The lease expires, Beta safely recovers it, and the recovery is measured.
4. Beta records a synthetic provider `SENT`. The lane becomes `SENT_DNR`; another acquisition attempt is denied as a duplicate-touch prevention.
5. A synthetic genuine human reply reopens one bounded next action.
6. A second synthetic buyer bounces with a 550-style provider result. OneWriter records `DEAD_ROUTE`, explicitly *not* buyer rejection.
7. The dashboard shows state, live leases, prevented collisions, prevented duplicate touches, stale recoveries, route failures, human reopens, and the tamper-evident receipt chain.

Run the proof locally:

```bash
cd competitions/emergent-builderfest-2026/onewriter
python acceptance.py
python -m unittest -v test_acceptance.py
python -O -m unittest -v test_acceptance.py
```

All three commands must pass without network access or third-party Python packages.

## Packet map

- `product_spec.md` — user stories, screens, state machine behavior, acceptance criteria.
- `emergent_master_prompt.md` — one-shot build instruction for the Emergent browser executor.
- `state_machine.json` — machine-readable state/transition contract.
- `demo_events.json` — deterministic synthetic replay with expected results.
- `acceptance.py` — offline engine, receipt chaining, replay verifier, CLI.
- `test_acceptance.py` — hostile collision, stale-lease, provider-truth, and tamper tests.
- `impact_evidence.md` — safe before/after evidence plan; no invented impact numbers.
- `submission_copy.md` — draft-only public listing copy.

## External authority boundary

This repository work does **not** authorize any Emergent account mutation, deployment, purchase, contest submission, public launch, buyer contact, email, DM, or form submission. A browser-capable executor must separately establish contest/account access, build the app in Emergent, deploy it, use it in the business, capture real evidence, re-census for a competing submission, and obtain the team's current single-writer publication authority before submitting.

OneWriter also does not replace existing live Muse/outbound controls merely because it models the same problem. Competition demo state is synthetic until the owner explicitly adopts a deployed build into operations.

## Contest fit

The product is designed around the contest's published scoring dimensions recorded in `#15421`: business impact/scale, problem solving, meaningful Emergent use, and UI/UX, while acknowledging that public upvotes are a separate distribution requirement. The source packet makes no claim that a submission, upvote, prize, ranking, customer outcome, or business impact has occurred.
