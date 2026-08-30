# NO MOCK-ONLY DELIVERABLES

Owner directive, 2026-08-21. Slack source: `1787308189.093099` (`p/slack-1787308189-093099.md`). Clarification: `1787308304.879819`. Leftover: DETAIL 31 / Rhea scope call — read it as **no mock-only deliverables**, then land it. This is a deliverable-quality rule, not an admission gate.

## Owner sentence (quote, do not rewrite)

> Build the real, usable implementation; do not substitute a mock, test-only artifact, or minimal skeleton for the requested thing.

Full owner line from Slack `1787308189.093099`:

> OWNER DIRECTIVE — effective immediately: mocks, tests, and “smallest possible implementations” are banned. Build the real, usable implementation; do not substitute a mock, test-only artifact, or minimal skeleton for the requested work.

## Scope

As literally worded ("tests … are banned") the sentence collides with the repo's own green test battery. The living scope is:

- **Banned:** shipping a mock, a test-only artifact, or a minimal skeleton *instead of* the requested thing.
- **Required:** the real, usable implementation. Tests that prove a real implementation are required, not banned.
- **Not banned:** the green test battery. A canary, regression, or `python3 -m unittest` run that measures the real thing is evidence, not a substitute.

Do not invent a prohibition that narrows capability, the open door, or credentials-without-gates. Missing speaker, seat, memory, or capability metadata never blocks a post or an action. This card does not add authentication, permission, approval, verb, path, or safety locks.

## What a peer does

1. Build the requested thing so a person or agent can use it.
2. Prove it with tests against that real implementation.
3. If a packet asked for a mock, a test-only stand-in, or the smallest possible skeleton *as the deliverable*, replace that stand-in with the real thing. Keep the tests.

Pins: [AGENTS.md](../AGENTS.md), [DIRECTIVES.md](../DIRECTIVES.md) item 67. Canary: `python3 test_no_mock_only.py`.

Open door. No auth. No gates.
