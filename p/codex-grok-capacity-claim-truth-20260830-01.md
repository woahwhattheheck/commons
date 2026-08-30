# Grok capacity claim truth repair

- Task: `codex-grok-capacity-claim-truth-20260830-01`
- Scope: the grok.com revenue orchestrator, Slack bridge handoff, focused tests, and operating contract
- Owner directive: a Grok seat with exhausted or unverified tokens must never claim or queue work

## Measured defect

The intake path returned `CLAIMED` and created a `fire_action` executor job for every non-echo message without any capacity observation. This let structural queue output look like completed provider execution even when grok.com had no tokens.

## Repair contract

- `EXHAUSTED`, `UNKNOWN`, missing, or incomplete capacity evidence returns `WAITING_CAPACITY`.
- Waiting capacity is silent: `post_reply=false`, empty `slack_reply`, and no executor job.
- `AVAILABLE` requires descriptive evidence plus `observed_at`; no credential enters the packet.
- Available intake says `QUEUED`, never `CLAIMED`, and explicitly reserves any work claim for a later submission receipt.

## Verification

- Fresh-main collision audit at `54cfd5bc0fa8ef4746b34f335aebad0019d97e03`: no changed-path overlap since lane base.
- `python3 -m unittest` across the orchestrator, Slack bridge/host, Grok integration, MCP, open-door, path-manifest, and landing-receipt suites: 186 tests passed.
- Focused exhausted/unknown-capacity cases prove zero Slack posts and zero `fire_action` calls.
- Pending final repository guards, merge, and exact current-main readback.
