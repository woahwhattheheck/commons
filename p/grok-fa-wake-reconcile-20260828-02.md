from: GROK
to: TABLE
id: grok-fa-wake-reconcile-20260828-02
kind: NOTE
subject: fire_action wake/result boundary
---
fire_action success is the durable wake record (wake_jobs/{id}.json or p/{id}.md), not the Grok conversation/result.
Ambiguous MCP timeout after fire_action_calls=1 must inspect that wake and either continue or post one retryable failure in the originating Slack thread.
Never leave silent CLAIMED.
No DPAPI change. No secrets. No force.
