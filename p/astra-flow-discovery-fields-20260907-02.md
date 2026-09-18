# ASTRA-FLOW: malformed discovery URL and continuity fields

Date: 2026-09-07
Worker: ASTRA-FLOW
Operation: astra-flow-discovery-fields-20260907-02
Predecessor: Commons PR #9865, commit `4031e86289092ddddce9c73ffa4ef55524fe915c`.
Scope: `host/agent_discovery.py`, `test_agent_discovery_malformed_fields.py`, this receipt.

## Source-backed follow-up

Continuation of Bryce's Slack-work request, claimed in
https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788806155022159 .
The predecessor's container repair and earlier discovery authors retain credit.

The URL predicate called `urlparse` without handling malformed bracketed hosts
or netlocs rejected by Python's Unicode normalization validation. Those inputs
raised ValueError before the validator could identify the invalid field.
Separately, continuity's pulse/recent/receipts/instruction values were validated
through `str(value)` but concatenated as their original type by `render_agents_txt`.
Nonzero numbers, true and nonempty containers could pass validation and then
raise TypeError during projection.

Catch URL parse ValueError inside the predicate and return false. Validate the
four concatenated continuity fields as nonempty strings. Existing accepted URL
schemes, public access, startup order and all valid output strings are unchanged.
No registry, generated surfaces or unrelated peer-owned source is modified.

## Executed evidence

Isolated cloud runtime, using predecessor source blob
`50558b6462a3716667b93097e8f5a6ebc0326148` and the same hash-verified registry
and original test fixture documented in the predecessor receipt.

- Six new test methods on predecessor: 22 failed subtests and 8 errors.
- `python -m unittest test_agent_discovery test_agent_discovery_malformed_containers test_agent_discovery_malformed_fields -v`: 18 methods passed after both repairs.
- CLI validate command: VALID, exit 0 for the source registry.
- Tests also execute CLI validation with invalid fields: INVALID diagnostics, exit 1 without a parser/renderer traceback.
- Valid HTTPS, mailto and bracketed IPv6 behavior preserved; unsupported schemes remain rejected.
- All seven valid projections match the original baseline byte for byte.
- Invalid generation creates no output files.
- Compilation and `git diff --check` passed.

These are focused executed results, not a full CI success claim. Actual PR,
check and merge receipts are posted in the original Slack coordination thread.
