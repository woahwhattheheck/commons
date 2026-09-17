# OneWriter — single-writer outreach control

**Operation:** `EMERGENT-BUILDERFEST-ONEWRITER-ZSOL-20260917`  
**Competition:** Kevin O'Leary × Emergent Builders' Fest 2026  
**Source state:** durable source packet only; `DRAFT_NOT_SUBMITTED`

OneWriter prevents a concrete multi-agent business failure: two workers independently decide to contact the same hot lead within seconds and both send. The failure is expensive because it looks like spam, damages trust, and creates contradictory follow-up ownership. OneWriter turns the pre-send coordination decision into an atomic, auditable workflow.

This packet is designed to be given to Emergent as the build contract for a working app. It does **not** send email, DMs, forms, or provider mutations. It does **not** grant contest-submission authority.

## Why this fits the contest

First-party contest page checked 2026-09-17:
`https://emergent.sh/ai-contests/kevin-oleary-emergent-builder-fest`

The page says:
- build a working app in Emergent for one real business problem;
- actually use it in the business;
- submissions close 2026-09-20 23:59 GMT;
- deployment is not submission;
- one active submission per participant/team;
- Business Impact / Potential to Scale is the largest rubric component at 30%.

OneWriter maps directly to the operations/team and revenue/sales categories: it coordinates lead ownership, prevents duplicate external touches, distinguishes route failures from human outcomes, and records evidence that can support real before/after measurement.

## Deterministic contract

A lane identity is:

`normalized organization × domain × route × purpose × opportunity`

The SHA-256 collision key is deterministic over canonical JSON. State is one of:

- `CLEAR`
- `LEASED`
- `HARD_DNR`
- `DEAD_ROUTE`
- `HUMAN_EVENT_REOPEN`
- `HOLD`

Important semantics:
- exactly one live lease per key;
- a concurrent claim loses while the lease is live;
- an expired lease can be recovered;
- only the current holder can record `SENT` or `BOUNCE`;
- `SENT` creates `HARD_DNR`;
- a provider bounce is `DEAD_ROUTE`, **not buyer rejection**;
- a retained genuine human event is the only event that reopens a fenced lane;
- no event in this source packet authorizes an external send.

See `state_machine.json` and `acceptance.py`.

## Synthetic demo

`demo_events.json` is deliberately synthetic (`*.invalid` domains). It demonstrates:

1. two agents claim the same lead three seconds apart — one gets the lease, one is denied;
2. provider `SENT` hard-fences the lane;
3. a later human reply reopens one bounded next action;
4. a stale lease is recovered;
5. a provider bounce creates `DEAD_ROUTE` without claiming buyer rejection;
6. a manual evidence `HOLD` blocks claims until genuine human evidence reopens it.

The expected replay contains 14 events across 3 lanes and measures only facts created by that synthetic replay. Those counts are **not** TJLabs production impact.

## Offline proof

Run from this directory:

```bash
python3 acceptance.py verify-machine state_machine.json
python3 acceptance.py replay state_machine.json demo_events.json
python3 -m unittest test_acceptance.py -v
python3 -O -m unittest test_acceptance.py -v
```

The verifier rejects duplicate JSON keys, non-finite numbers, semantic contract remints, authority escalation, duplicate event/provider/human evidence IDs, out-of-order timestamps, invalid lease types, non-holder provider outcomes, expired-holder outcomes, and unknown event fields.

## Emergent build handoff

Use `emergent_master_prompt.md` as the build prompt. The deployed app must then be used on a real TJLabs coordination workflow and produce measured evidence using `impact_evidence.md` **before** contest copy is converted from draft evidence placeholders into real claims.

`submission_copy.md` is intentionally `DRAFT_NOT_SUBMITTED`.

## External authority boundary

This repository packet grants none of the following:
- external email/DM/form sending;
- provider mutation;
- contract/signature authority;
- payment/cash/revenue claims;
- contest submission;
- paid Emergent upgrade/spend;
- public upvote campaign.

Any real external communication remains separately single-writer coordinated. Any contest submission must be reconciled against the platform's one-active-submission rule immediately before submission.
