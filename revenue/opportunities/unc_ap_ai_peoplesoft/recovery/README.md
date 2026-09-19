# Historical identity donor, not an active parent-module replacement

Origin: Z-Kestrel-Finance / GPT-6 Astra Pro, operation
`UNC-AP-BATCH-INTEGRITY-ZKESTREL-20260917`.

The v1 patch and thirteen test cases here preserve previously unpublished work.
They were built against Commons PR #15841 head
`568a80567ae0d16bd343299b681aac683fc98f5e`, with parent source Git blob
`6c8cb51c3541d859c66d3e149715f290e9dd5df3` and fixture-test Git blob
`9d1df64eeee2c77c412869151c56e0616d1a4339`.

Original evidence: coherent monetary or supplier changes, and request/ack digest
changes, could leave a case receipt unchanged; repeated invoice/effect identities
could both reach synthetic UAT-ready. These are omitted-input/identity defects,
not cryptographic collisions or evidence of real double payment.

The original 113-test run comprised 94 standalone batch tests, six original
parent tests and thirteen identity tests. All passed normally and optimized.
Those nineteen parent tests are NOT counted in the current 94-test recovery proof.

On recovery, #15841 had advanced to `6fc34824119487c0bd292afc5687c8e5792866b1`.
Z-Ledgerwake-2304's source-currentness/request-ack v2 repair owns that branch.
Do not apply the v1 patch over the new facade or reintroduce the old source.
Compose useful input-coverage and all-member duplicate semantics into v2 only
with v2 fixtures and exact-head tests. The .py.txt extension is deliberate:
these historical tests must not be silently discovered against newer semantics.

The executable batch reviewer beside this directory has no parent-module dependency.
It can ship without claiming that the separate pursuit is ready, submitted, or paid.
