# OWNER CONTEXT — optional host-side display digest

Directive 10 leftover: a host outside this static tree that can add
optional owner context without publishing network material.

This is a **display/context lane only**. It may annotate the owner's
interface with a privacy-preserving context digest. It cannot control
participation, reads, writes, execution, or authority. Identity
verification is not future work under the NO-AUTH law.

Cite `BRYCE-1787134106972-vr8fo8`. Do not remint.
Law: `admin-no-verification-loop-20260819-01`. Do not remint.

Two-slot hashed enrollment stays LIVE on `owner-net.html` /
`owner_net.js` / `owner_net.py` / `owner.json`. This leftover does not
overwrite those slots.

## Rule

1. Display only. authority stays false. from= stays a claim.
2. Hash `pepper + LF + normalized public IP`. Pepper version `v1` is
   `commons-owner-v1`. Rotation is versioned, never silent.
3. Never publish a raw IP or reversible network material. Responses,
   logs, doctor output, and `owner.json` are scanned.
4. Client-supplied digests cannot become a slot. via= is a hint.
5. Missing peer, missing host, or failed probe fail **open**.
6. Live public URL is doctor-probed. Unconfigured is
   `EXTERNAL_HOST_ACTION`, not invented LIVE.
7. FINDER-FAILED / FINDER-UNVERIFIED plus the search space. Never 0.
8. no auth. no gate.

## Measure

```bash
python3 host/owner_context.py simulate
python3 host/owner_context.py doctor
python3 test_owner_context.py
python3 integrations/owner_context/canary.py
python3 open_door_guard.py --diff origin/main HEAD
```

Talk that restates the leftover without this adapter is **CLAIMED**.
A missing public URL after the adapter is on main is
`EXTERNAL_HOST_ACTION`, not a remint.

## Desk

`land.js` `isOwnerContextTalk` names host-outside-this-static-tree /
richer-context-only-display talk CLAIMED until this leftover is on
current main. `ownerContextState` names the measured instrument.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260905-20 — do not remint.
