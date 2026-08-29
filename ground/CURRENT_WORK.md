# Current work

This file is the law for the unfinished-now ledger.

**DIRECTIVES.md is historical.** Its `OPEN` / `HALF` / `BUILT` sentences are receipts of what was asked and what was claimed. They are not the now-queue. Do not rewrite them away. Do not treat a stale `OPEN` line as an invitation to rebuild working code.

**todo.html is a view of DIRECTIVES.md.** It must keep saying so. Unfinished now lives here:

- human: [current-work.html](../current-work.html)
- machine: [CURRENT_WORK.json](./CURRENT_WORK.json)
- instrument: [host/current_work.py](../host/current_work.py)
- sibling projector (not a second queue): [open-work-structured-ids-on-current-main.md](./open-work-structured-ids-on-current-main.md) · [open-work-listing/](./open-work-listing/) · [host/open_work.py](../host/open_work.py) · pointer [OPEN_WORK.md](./OPEN_WORK.md)

## Close rule

A current item closes only from main evidence:

- official main SHA is 40 hex characters
- every `claimed_paths` entry exists on that SHA

Chat text, Slack, ntfy 200, an open PR, a claimed merge, or a Pages card is not close evidence.

Structured work-order ids (`WORK ORDER`, `OWNER LAND ORDER`, `kind: ACTION`) are classified by the sibling projector into OPEN / LANDED / DEAD_CLAIM / SALON / NOISE. LANDED only when `p/{id}.md` exists at official current main SHA. Slack CLAIMED is not a land.

## Kinds

- `BUILDABLE` — a peer can land it on current main through an open road.
- `OWNER_PLATFORM` — needs an external owner or platform act. Peers do not fake the act.
- `DEVICE_PINNED` — hazardous device operation. Do not fire it from this ledger. Do not invent Muhlnickel destinations.

## Add work

Peers add their own item. They get a durable job id (`^[A-Za-z0-9._-]{8,80}$`).

Preferred add-work road is the already-landed GPT → GROK SHIP LOOP, not a second board:

- [gpt-grok-ship-loop.html](../gpt-grok-ship-loop.html)
- skill: [.agents/skills/gpt-grok-ship-loop/SKILL.md](../.agents/skills/gpt-grok-ship-loop/SKILL.md)

Also legal: append a row to `ground/CURRENT_WORK.json` on a unique branch and merge to current main; file `p/{id}.md`; GitHub issue `label=board`.

Same id + identical bytes is idempotent. Same id + different bytes is `CONFLICT`. Never overwrite.

## What this ledger is not

- not `right-now.html` (buyer / revenue desk)
- not `builds.html` (permit SOP)
- not `ledger.html` (resource census)
- not `feature-tracker.html` (shipped-state tracker; source vs live)
- not `listing-registry.html` (listing drafts; not unfinished now)
- not `payment-capability.html` (payment rails; not unfinished now)
- not `ground/MANUAL.md` open-job scrape
- not a Cursor / auth / approval / branch-lock / peer gate
- not [opportunity.html](../opportunity.html) (non-dilutive funder/program desk; composes this ledger)

Non-dilutive commercialization now: [opportunity.html](../opportunity.html) · [proof-to-proposal.html](../proof-to-proposal.html) · [OPPORTUNITY_REGISTRY.md](./OPPORTUNITY_REGISTRY.md). Those doors compose this ledger; they do not replace it. They also compose, and do not remint, [listing-registry.html](../listing-registry.html).
