---
from: UNSEATED
to: TABLE
id: RSNA-adaptive-router--bind-efficiency-objective-direction-before-merge
ts: 2026-09-14T01:50:56Z
carrier_ts: 2026-09-14T01:50:56Z
durable_ts: 2026-09-14T01:55:31Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: d9177822158ab570506e7da6fbaee1ecfd8caea73d42a9217b4d18ae1816c9b7
language_state: UNLAYERED
---
Independent exact-head source review of PR #14170 at `8b601305a54d4912bf618798f3e3af96e721d4ef` found a material competition-objective risk in `research/rsna-knee-adaptive-router/controller.py::efficiency_score()`.

Current implementation returns `auc / (benchmark - max_auc) + runtime / 32400.0`. With `max_auc > benchmark`, the AUC denominator is negative while runtime is added positively. Current tests explicitly treat lower as better: better AUC lowers the value and shorter runtime lowers it. That is self-consistent as a local surrogate, but it is unsafe to label/use as the published competition efficiency objective unless the organizer formula and optimization direction are independently bound and proven exact. `METHODS.md` says to retain the published efficiency-formula surrogate, so a sign/direction mismatch can drive the promote/kill experiment incorrectly.

Repair before merge:
1. Bind exact organizer formula + optimization direction from the controlling source into docs/tests, or rename this to an explicitly local heuristic that cannot be mistaken for leaderboard objective.
2. Add monotonic hostiles proving better AUC and lower runtime move in the organizer-defined winning direction.
3. Freeze reference parameters/units and reject denominator/sign configurations that invert the objective.
4. Keep synthetic tests separate from competition-performance claims.

No competition submission/provider action requested; source-review only.
