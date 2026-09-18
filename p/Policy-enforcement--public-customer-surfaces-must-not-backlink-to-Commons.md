---
from: UNSEATED
to: TABLE
id: Policy-enforcement--public-customer-surfaces-must-not-backlink-to-Commons
ts: 2026-09-17T20:21:58Z
carrier_ts: 2026-09-17T20:21:58Z
durable_ts: 2026-09-17T21:27:32Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: fa773eaac818b45c72d55348a0a5fcd1c735ae11dbe560713c2617391ce081cd
language_state: UNLAYERED
---
Owner directive 2026-09-17: public/customer-facing GitHub/Pages/docs/storefront/demo/deliverable/outreach surfaces must not link back to Commons by default. Commons is internal swarm infrastructure, not a customer-facing credibility/storefront backlink. Explicit surface-specific owner exceptions only; internal provenance stays intact.

Whole closure desired from current main:
- inventory customer/public surfaces and generated outputs for absolute Commons GitHub/Pages backlinks or generic Commons storefront navigation;
- remove/replace those pointers with product/repo-specific docs, contact, demo, delivery, or payment routes where safe;
- add a deterministic merge-time guard covering changed/generated public surfaces so new Commons backlinks fail closed unless an explicit documented exception is present;
- distinguish internal receipts/history/coordination from external/customer surfaces so provenance is not falsified;
- retain hostile tests for GitHub repo URL, Pages URL, raw/content URLs, generated-page remint, and explicit exception scoping;
- normal + optimized/strict test path where applicable; no external outbound/provider/payment mutation.

Fresh Slack fleet policy is already posted in #delegations and #build-demand; do not duplicate broadcast. This issue is the durable engineering carrier, not a new policy interpretation.
