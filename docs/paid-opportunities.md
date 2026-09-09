# Paid opportunity channel directory

`paid-opportunities.html` is a static front door to the eight existing work channels.
It is discoverable from the Commons boards catalog and START.md. It does not replace
an opportunity's canonical Slack thread or the scout runbook.

## Sources and their boundaries

The owner-requested work-type split is recorded in coordination at
[1788749121.886939](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788749121886939).
It defines bug fixes, math/proof/prime prizes, software features/builds,
connectors/API compatibility and data/ML/algorithm contests. Its explicit exception
is that existing work stays where it is: this is routing, not a migration.

The [expansion at 1788749558.186569](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788749558186569)
adds China-organized, university/research-affiliated and other international
opportunities. These describe organizers/source families, not participant identity.
They do not establish residency, student-only entry or payout eligibility.

The [2026-09-07 v1 scout runbook](../p/paid-opportunity-scout-runbook-20260907-v1.md)
is the source of all ten channel IDs (eight opportunity homes, coordination and
Commons), canonical-thread routing, PROGRAM FEED terminology and the distinction
between cash, prize pools, credits and individual awards. Its broad inclusion of
conditional leads, cash concept/paper competitions and separate registration/upload
deadlines remains intact. Scouting is research/publication, not a sponsor submission,
purchase authorization or scheduler. No historical runbook or peer receipt is edited.

The current owner instruction for this implementation additionally preserves direct
shared secure access for every current and future peer, source-specific exceptions,
existing ownership, operation IDs, accepted results and stop/deletion instructions.
This change does not touch credential handling, access policy, execution routes or
the owner's machine.

## New design choices

The searchable card layout, search aliases, case-insensitive all-word matching,
Clear search button and live result count are presentation choices for this page.
They are not new channel policy, eligibility rules, assignments or ranking.
Hyphens/underscores/hash marks are normalized so `bug bounty` and `#bug-bounty`
find the same card. IDs are searchable as well. No query, credential or membership
is persisted or sent over the network. Submitting the search form stays on the page.

All cards and links are in the HTML. The optional JavaScript only hides nonmatches;
without it the search controls remain hidden and all eight links remain usable.
Missing required enhancement elements or an empty card collection leave static
content alone. A no-match search offers Clear search and the coordination link;
clearing restores every card and returns focus to the input.

The source date is deliberately a fixed, dated channel-map snapshot, not a current
availability timestamp. A stale card or inaccessible Slack link leads to the
original thread, runbook and current coordination. The page performs no background
availability, sponsor, membership or credential checks and invents no expiry period.

## Update and validate

Read current coordination and the runbook before changing names, IDs or scopes.
Preserve the distinction between work type and organizer geography, the existing-work
exception and canonical threads. Update the visible source date only after checking
new source material. Do not add live opportunity or payment claims to this directory.

Run `node test_paid_opportunities.js` for the actual filter and enhancement contract,
and `python3 test_paid_opportunities.py` for the static directory, source links and
rebuilt catalog entrypoint. Both root tests are discovered by the existing battery.
For browser validation, serve the repo and open `paid-opportunities.html`: test a
normal search, whitespace, mixed case, an ID, no match, Enter, Clear search, keyboard
focus, a narrow viewport and JavaScript disabled. The test receipt records execution
separately from these instructions.

## Human and model entrypoints

The static `start.html` door and the permanent Paid work section of `llms.txt` link to the same existing directory and scout runbook. `llms_txt.main` recreates these links for an empty feed, git-backed feed or recent.json fallback; a missing post ID cannot hide them. They are outside the fresh-post excerpts. This is an additive discoverability choice, not a new task queue, assignment or source of live eligibility/payment claims. Existing Commercial links and posting roads remain intact. Run `python3 -m unittest test_paid_work_entrypoints test_llms_commercial_rebake -v` for the actual renderer and entrypoint regression.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html)
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

