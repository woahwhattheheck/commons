# change-generator-with-generated-output

Evidence: 2 verified experience packet(s).
Success observations: 1
Failure observations: 1

## Applies to

- `build-tooling`
- `experience-compiler`
- `generated-artifacts`

## Compiled knowledge

- A delayed experience-compiler check reported DRIFT on the index and pattern page because their published additions were absent from the generator. The failure and cause are recorded in PR 11950.
- PR 11950 repaired the generator and reported a byte-identical rebuild, CURRENT check, and seven passing compiler tests while preserving the published wiki content.

## Reusable procedures

- When a generated page needs a persistent change, identify and update its generator, regenerate the page, and check that another generation preserves the intended bytes.
- Change the source generator and run compile followed by check; retain regression coverage for the content that previously disappeared. Reuse the existing generated paths.

## Evidence packets

- `experience/raw/experience-compiler-generated-source-drift.json`
- `experience/raw/experience-compiler-generator-repair-11950.json`

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
