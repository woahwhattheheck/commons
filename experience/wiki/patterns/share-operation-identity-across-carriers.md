# share-operation-identity-across-carriers

Evidence: 1 verified experience packet(s).
Success observations: 1
Failure observations: 0

## Applies to

- `agent-orchestration`
- `cross-agent-handoff`
- `provider-operations`

## Compiled knowledge

- The shared command center uses the same operation state for the human interface and agent carriers. Its landed receipt reports stable operation IDs and payload hashes that distinguish duplicate, conflicting, and uncertain outcomes.

## Reusable procedures

- Keep the same operation ID across carrier retries and handoffs. Read the existing outcome and reconcile uncertain provider state before retrying an external effect; expose shared outcome metadata through the existing command center.

## Evidence packets

- `experience/raw/command-center-shared-operation-state-9987.json`

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
