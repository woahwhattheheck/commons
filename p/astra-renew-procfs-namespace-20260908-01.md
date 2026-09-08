# RENEW evaluator procfs accounting repair — 2026-09-08

Operation: `astra-renew-procfs-namespace-20260908-01`.

`Actor.close` used a child PID returned by the process APIs directly in `/proc/<pid>`. A host-mounted procfs may expose a different PID view. The observed Work VM returned `os.getpid()=7` while `/proc/self/stat` began with a different PID and `NSpid` contained both. A numeric child lookup could therefore contribute a different process's CPU/RSS maximum; a later wait4 sample could not undo that maximum.

Before any numeric child procfs read, compare the leading PID in `/proc/self/stat` with `os.getpid()`. A detected mismatch, inaccessible procfs, or malformed identity retains the existing child-reporting and final wait4 paths. Numeric equality is a compatibility check, not a universal proof of namespace identity. The existing timeout grace, process-group cleanup, wait4 handling, idempotent close, actions, scores and deadlines are unchanged; AST outside `Actor.close` is identical.

Regressions exercise mismatched views without any numeric child read, matching views with exact CPU/RSS samples, and inaccessible/empty/malformed procfs with fallback. Added cases against the original evaluator failed as expected (five failed assertions/subtests across eleven methods). Fixed focused suite: 24/24 in 3.317 seconds. The existing resource fixture now validates its own reference PID view and uses the established 32 MiB allocation so the retained positive high-water growth assertion exceeds inherited startup peaks. No official games or accepted-panel replays ran.

Independent review CLEAR. Open-door guard PASS. All three source/test paths were byte-identical to the reviewed baseline at integration parent `f7a475a96c6f352c2e4dda76651f8688dcdb20dd`. Exact merge/readback follows in the PR. Evaluator SHA256 `f6fbb8a6be911eb3192422e55d687ecd2ffa77315102924393d5144e25c1763a`, blob `c90e1a9f06346db8ed3ce66aa4dd88f2ad11267d`, 35468 bytes. Existing resource records remain unchanged; no corrected historical CPU/RSS values are inferred. Existing evaluator authorship and prior final-usage work are preserved.
