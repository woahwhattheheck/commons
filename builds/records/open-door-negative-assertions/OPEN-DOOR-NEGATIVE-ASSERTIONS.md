# Open-door guard: negative-assertion statement scope

## Reproduced gap

The prior scanner treated any active source line beginning with a recognized
negative assertion as wholly exempt. In Python, one physical line can contain
more than one executable statement. These added lines therefore returned a pass:

```python
self.assertFalse(flag); SEAT_GATE = True
assert not hasattr(module, "gate"); REQUIRE_IDENTITY = True
self.assertFalse(flag) or REQUIRE_PERMISSION()
```

The exemption also operated independently on each line of a multiline negative
assertion, which could expose quoted forbidden text to the surrounding window
rules. This is a direct synthetic-diff reproduction, not evidence that such a
bypass was merged into production source.

## Change

The original `open_door_guard.py` implementation is retained byte-for-byte as
`open_door_guard_core.py` (Git blob `861958e91177fedd09db974345a2838387e7f2b7`).
The small front module loads and re-exports that scanner, then changes only how
negative regression assertions are suppressed:

- non-Python languages retain the existing textual heuristic;
- contiguous added Python lines are dedented and parsed;
- only one standalone `assert` or recognized assertion-call expression is eligible;
- strings and comments are blanked before the existing line rules are checked, so a forbidden identifier used as executable assertion code is never hidden;
- walrus expressions, boolean-expression tails, semicolon-separated statements,
  and statements appended to a multiline closing line remain visible;
- quoted semicolons, trailing comments, ordinary standalone negative assertions,
  and a truncated first line of an otherwise unchanged multiline assertion keep
  their prior exemption.

The wrapper records an explicit core path in the inherited environment because
the existing actual-Git workflow matrix copies the scanner into an isolated
fixture. Normal repository execution loads the sibling directly. Both scanner
implementation files are self-excluded, matching the existing self-exclusion of
`open_door_guard.py`; active application source remains covered.

All existing line rules, hard-rule ordering, directive/prohibition phrases,
HTML contexts, structural windows, diff parsing, reporting, and workflow base
selection remain unchanged. No admission rule was removed or added.

## Executed checks

`test_open_door_guard_negative_assertions.py` runs twenty-seven direct unified-diff
cases through the actual scanner module.

- Wrapper: 27 passed, 0 failures, 0 errors.
- Exact prior scanner: 13 passed, 14 failures, 0 errors.
- The fourteen prior failures cover semicolon/boolean tails, complete and
  incomplete gate calls embedded in
  `assert` and assertion-call expressions, a walrus expression, a structural
  schema tail, and the multiline negative-quote false positive.
- Python compilation passes for the wrapper, unchanged core, and focused test.
- A copied-wrapper subprocess with no sibling core successfully consumes the
  inherited explicit core path and rejects the semicolon-tail witness.

The authoritative existing `test_open_door_guard.py` workflow matrix is left in
place for hosted execution. No new workflow or duplicate dispatch is introduced.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
