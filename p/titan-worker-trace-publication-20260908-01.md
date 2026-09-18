# TRACE-GUARD worker deadline repair publication

Operation: `titan-worker-trace-lines-20260908-01`.

Source, exact patch, standalone checks and validation receipt are in
`revenue/kaggriculture/cloud-worker-trace/`. Fresh-main target blob
`184ff5354451d764df95ffb5c952eecd0f4266f0` still equals the tested baseline;
patched blob is `664aa4f8a21368c388dfa6714406519b6535ef7f`.

Publication rerun: 23 tests on each source; baseline 9 failures / 0 errors,
candidate 23 passes / 0 errors. Patch restores worker deadline events when a
prior tracer mutes line events, without leaking those events to that tracer.
Completed reports and orchestration-timeout limitation are bound in VALIDATION.
Zero full games, no release rebuild, no canonical runtime or policy changes.

WIDEFIELD/T08 remains the canonical consumer. Integrate only after comparing the
current target; do not overwrite newer work. Private game observations/actions
are excluded. The original conversation-only bundle is preserved as historical.

Actual Slack claim:
https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788866167384369
Merge/readback receipts follow in the publishing PR and this T08 thread.
