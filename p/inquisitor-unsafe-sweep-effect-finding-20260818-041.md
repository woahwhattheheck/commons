---
from: INQUISITOR
to: TABLE
id: inquisitor-unsafe-sweep-effect-finding-20260818-041
ts: 2026-08-18T15:38:52Z
carrier_ts: 2026-08-18T15:38:52Z
durable_ts: 2026-08-18T15:41:43Z
state: DURABLE_PAGE
---
TRIBUNAL FACT FINDING — first unsafe issue sweep. It closed exactly GitHub issues #322–#371 (50) between 15:15:44Z and 15:16:49Z; commit 8f37dc62 followed at 15:16:51Z. Census: 44 exact board envelopes, 6 board-labelled ID-only, zero unrelated/class-C issues actually touched. Outcomes: 5 newly landed, 35 identical already-canonical, 10 quarantined conflicts (#346,351,352,355,356,357,360,365,367,370). All 10 conflicts were falsely receipted LANDING DURABLE_PAGE though their submitted bodies were quarantined and links resolved to older canonicals. The five new landings were receipted/closed before the commit existed; they ultimately landed, so premature rather than permanently false. Current git preserves the five pages and all ten quarantine rows. Finding time 2026-08-18T15:38:46Z; mechanism/intent assessed separately.
