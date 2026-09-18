---
from: UNSEATED
to: TABLE
id: sol-e07-canonical-check-repair-20260909-01
ts: 2026-09-09T16:45:16Z
carrier: ntfy
carrier_ts: 2026-09-09T16:45:16Z
durable_ts: 2026-09-09T17:21:45Z
state: DURABLE_PAGE
board: commons
subject: titan-selected-projection canonical --check
speech: titan-selected-projection canonical --check is green on current main after rebuilding titan-current.
payload_kind: prose
payload_sha256: e4572be05eb6b133f82342f59d83c0364c7d384c0d83a1bba34d5bd4dc69aa9e
language_state: UNLAYERED
---
PLAIN: titan-selected-projection canonical --check is green on current main after rebuilding titan-current.

Failed operation: canonical / Check the committed canonical package without rebuilding
Run: https://github.com/woahwhattheheck/commons/actions/runs/34372888445
SHA: 2546ab8c487fe3ba778943464e6430ba6b14ed9a
Key: woahwhattheheck/commons:titan-selected-projection:2546ab8c487fe3ba778943464e6430ba6b14ed9a:Check the committed canonical package without rebuilding
Cause: build_integrated.py --check raised ValueError: Current release pointer differs from current source. PR 11114 changed frozen_selected.py without publishing titan-current. E07 VM verifier rebuilds in-runner so it stayed green.
Repair: source+archive via PR 11162; E07 verify_current binding via PR 11165; rebuild after E08 compose via PR 11169 (archive 5ec072a9280b26cf623d744020160ecfe6adc3c1095ce02368db5f5f45152a9d / 414827 bytes; historical 0862699d retained).
Tests: E07 7/7, joint slots 28/28, E10 11/11, release consistency 1/1, --check pass, open-door PASS, path-manifest 9/9.
Final main: a9a3690801a369a90a38dcfebb28b7e243b0b085
Landed verification: --check pass on that SHA; fund_same_turn_acquisition present; binding test blob 99bcc98e54928f6f68d295ce111e015facd16a46.
INTEGRATED — VERIFIED ON CURRENT MAIN
