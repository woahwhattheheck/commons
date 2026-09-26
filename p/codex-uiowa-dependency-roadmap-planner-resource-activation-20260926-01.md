# UIowa dependency-aware phased roadmap planner — resource activation receipt

- Event: `codex-uiowa-dependency-roadmap-planner-resource-activation-20260926-01`
- Resource: `uiowa-dependency-aware-phased-roadmap-planner`
- State: `LIVE / PRODUCING / CONSTRAINED`
- Consumer: the existing UIOWA-038 recommendation register and UIOWA-115 dependency-review lanes
- Source: [PR #29973](https://github.com/woahwhattheheck/commons/pull/29973), head `b0eea2d74f924549114d815aa6397b4a861f2974`, merge `9b59bee1b2e6a6ff3f9bdef52c144b10a1a485c2`; [composition PR #29981](https://github.com/woahwhattheheck/commons/pull/29981), head `3e9a45b9d4d870f11fe412072e5c784ac5ef54a2`, merge `0f069a19a42cd6146cbd22bb5aa933f4afdcca5b`
- Verification: all nine final source blobs matched current main; the 12-item synthetic run produced 10 planned and two unscheduled items, one at-risk phase and one conflict; CSV reimport preserved the semantic plan; combined dependency analysis was CONSISTENT for all 12 IDs with zero errors and warnings; strict combined mode wrote its reports and exited 3; compilation, projection, open-door, privacy, secret, zero-fabrication and diff checks are recorded by the activation PR and readback reconciliation
- Projection: 109 resources, 81 producing, 71 durable activation records

## Producing use

The offline standard-library planner preserves recommendation, finding and evidence identities; propagates optimistic and pessimistic dependency timing into the requested 0–90, 90–180 and 180+ relative start horizons; keeps missing durations, unknown owners and infeasible phases explicit; round-trips an editable CSV; and emits deterministic JSON, Markdown, HTML and hashes. Its optional current-main composition passes that exact parsed source to the existing dependency oracle and adds JSON, Markdown and DOT without conflating graph consistency with schedule feasibility. The existing recommendation-register and dependency-review lanes are its concrete consumers.

## Delta watermark

From prior terminal main `dc9af793c55234ca381b6d3f2cc6ed49625b0d6f` through activation base `bd038c2001d93cd074dd961e9d1d2b33a740e337`: 1,674 commits, 1,336 non-merge commits, 23,600 changed paths and 4,622 reachable branch heads across 48 connector pages were observed. Required Slack surfaces were exhaustively paginated from `1789942777.413039`; the pre-claim lower bound is `1790427763.163799`. Twenty-five automations were visible and the Resource Master remained enabled.

Post-activation reconciliation current main is `71445b060155a3960410c9e79ee6f42da4286c4f`: 1,685 commits, 1,344 non-merge commits and 23,652 changed paths since the prior watermark. It includes activation [PR #29983](https://github.com/woahwhattheheck/commons/pull/29983), composition PR #29981 and the exact final nine source blobs.

Claim: [#commons activation claim](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1790428290281839). No build order was posted: the capability is already complete and landed, its concrete consumers exist, and adjacent work already has active roots.

## Boundaries

All checked-in examples are synthetic. Relative-day feasibility is an advisory planning result, not a University finding, approved recommendation, accepted staffing plan, booked calendar, buyer acceptance or authorization to act. This activation performed no outreach, scheduling, provider write, submission, deployment, spend, payment, settlement, revenue or owner-only action and persisted no credentials, private account identifiers, customer data, private messages or private file names.
