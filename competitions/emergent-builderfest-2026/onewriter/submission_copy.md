# DRAFT — Emergent Builders' Fest submission copy

**Status: DRAFT_NOT_SUBMITTED. Replace bracketed evidence fields only with verified deployed facts.**

## Title

OneWriter — Stop AI agents from double-contacting the same customer

## Short description

OneWriter gives multi-agent teams a single, auditable answer to "who is allowed to contact this external party now?" It atomically grants one bounded writer lease, blocks collisions and post-send duplicates, distinguishes dead routes from human rejection, safely recovers stale work, and records a tamper-evident receipt for every accepted or denied action. It coordinates outbound authority; it never sends the message itself.

## Problem

AI-augmented teams move fast enough that two workers can independently reach the same hot lead within seconds. Each message can be individually reasonable while the combined behavior looks spammy, destroys trust, and makes the team's state impossible to reconstruct. A shared spreadsheet or "check Slack first" convention is not atomic and fails exactly when several agents act at once.

## Solution

OneWriter normalizes organization, route, purpose, and opportunity into one deterministic collision key. Exactly one worker can acquire a bounded lease. Concurrent claimants are rejected with a receipt. A verified provider send hard-fences that exact lane from duplicate touches until a genuine human event reopens one bounded next action. A bounce becomes `DEAD_ROUTE`—never fabricated "buyer rejection." Expired work can be safely recovered. Every transition, including denials, is hash-chained for replay.

## Demo

The public demo uses synthetic data only. Agent Alpha and Agent Beta claim the same Acme Fabrication lane one second apart; only Alpha wins. After Alpha's lease expires, Beta safely recovers the lane, records a synthetic provider send, and a later duplicate attempt is blocked. A genuine synthetic reply reopens one next action. A separate route demonstrates a 550-style bounce becoming `DEAD_ROUTE` rather than a fake customer outcome. The receipt inspector verifies the complete chain offline.

## Real business use / impact

OneWriter was built around a real operating requirement at Token Junkie Labs: preventing concurrent workers from duplicating outbound touches. Before final submission, replace this paragraph with owner-cleared measured evidence from the deployed app:

- deployed use window: **[NOT YET MEASURED]**
- outbound intents observed: **[NOT YET MEASURED]**
- concurrent collisions prevented: **[NOT YET MEASURED]**
- post-send duplicate touches prevented: **[NOT YET MEASURED]**
- stale lanes safely recovered: **[NOT YET MEASURED]**

No fabricated savings, conversion lift, customer count, or revenue claim should be added.

## Why Emergent

**Replace after browser build with specific verified implementation details.** Describe which Emergent-generated frontend/backend/database/auth/deployment capabilities are actually present and how its atomic backend state transition protects the business workflow. Do not claim tools that were not used.

## Public call to action

Try the synthetic collision demo, race the two agents, inspect the losing receipt, then verify the hash chain. The point is simple: faster agents need stronger coordination, not more outbound volume.

## Submission checklist

- [ ] App built with Emergent and deployed.
- [ ] All synthetic demo flows exercised successfully.
- [ ] Export compared against offline contract/tests.
- [ ] Real internal use performed with owner authorization.
- [ ] Aggregate impact fields measured and privacy-reviewed.
- [ ] No private lead/customer data visible.
- [ ] Emergent usage paragraph updated from verified build facts.
- [ ] Fresh contest/account collision census confirms no competing active submission.
- [ ] Single-writer submission authority obtained.
- [ ] Platform readback captured after submission.
