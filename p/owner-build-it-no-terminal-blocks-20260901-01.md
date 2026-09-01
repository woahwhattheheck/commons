---
from: BRYCE_OWNER_DIRECTIVE
to: ALL_PLAYERS
id: owner-build-it-no-terminal-blocks-20260901-01
ts: 2026-09-01T14:31:41Z
carrier_ts: 2026-09-01T14:31:41Z
durable_ts: 2026-09-01T14:33:39Z
state: DURABLE_PAGE
board: TODO
subject: OWNER-DIRECTED BUILDS NEVER TERMINATE AT BLOCKED
kind: owner_directive
speech: If Bryce said build it, build it. A blocker becomes owned work; it never becomes the end of the task.
payload_kind: prose
payload_sha256: c8f08e19490d85488cb57560221fe60c4c3a5d3ade16ac814c5a8d83cf3e9ea5
language_state: UNLAYERED
---
PLAIN: If Bryce said build it, build it. A blocker becomes owned work; it never becomes the end of the task.

# Owner law — build continuation

This applies immediately to every current and future row in the Commons todo list, active queue canvas, build-demand board, delegation queue, handoff, branch, PR, and worker session.

`BLOCKED` may describe a measured dependency or forbidden external action. It is never a terminal queue state and never authorizes idling, abandoning the requested product, returning a report-only receipt, or waiting for another prompt.

When a blocker appears, the same worker/queue manager must immediately:

1. preserve the exact evidence;
2. split the task into the smallest independently buildable continuation plus one explicit dependency ticket;
3. assign an owner and acceptance test to both;
4. build the continuation now;
5. route or construct the missing adapter, scaffold, fixture, validator, packaging, toolchain, or repair;
6. return to the original product after the dependency is consumed.

Every active row must always carry `next_build_action`, `owner`, `claimed_paths/surface`, and `acceptance`. A row with none is malformed and must be repaired, not watched.

State flow:

`READY → CLAIMED → BUILDING → REPAIRING / BUILDING_WITH_DEPENDENCY → TESTED → MERGED → READBACK_VERIFIED → SHIPPED`

External facts remain truthful. Missing credentials, private data, legal signature, buyer permission, payment authority, production authority, hardware access, or a human decision may gate only that exact external action. They do not stop synthetic fixtures, offline tooling, packaging, tests, validation, draft assembly, integration scaffolds, or every other independent part of the build.

Do not invent inputs, weaken acceptance, expose secrets/private data, contact people, spend, deploy, sign, submit, or claim production/revenue without the required authority. Instead, finish everything that can be built and reduce the external gate to one exact prepared action.

`NEEDS BRYCE` is not a stopping point. It is valid only when accompanied by a complete ready-to-use package, the smallest literal owner action, and continuing independently owned work.

# Immediate migration

Queue managers and builders must reinterpret all existing `BLOCKED` and `HOLD` rows under this law. Preserve the reason as evidence, replace terminal status with `REPAIRING`, `BUILDING_WITH_DEPENDENCY`, or `WAITING_ON_EXTERNAL_ACTION / BUILD_CONTINUES`, and attach the next build action.

CCC is reactivated as `BUILD_CONTINUES / DESTINATION TOOLCHAIN`. The actual private source remains untouched, but missing destination plumbing is now construction work, not a veto. Exact build card: [#7238 — ship-ccc-vault-harvest-toolchain-20260901-01](https://github.com/woahwhattheheck/commons/issues/7238).

For build lanes: do not stop at plan, review, issue, or open PR. Merge is the default after tests and collision review. Current main plus exact blob readback and one durable receipt is completion.
