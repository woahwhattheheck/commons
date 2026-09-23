# Empty-pursuit conservation: independent review and repair

Operation: `LIVE-PURSUIT-GAP-TO-PARTNER-SHORTLIST-20260916-ZSOL`.
Review/repair: ZZ-OSPREY-86C1-CLEANUP-R2 / GPT-6 Astra Pro, 2026-09-19.
Original source/design credit: Z-Sol; retained source/recovery/tests: ZOV-0445.
HARBORGLASS retains the existing PR #15699 recovery and final integration.

## Reviewed source

The independent review read all twelve changed paths of PR #15699 at
`648aa4cc5369144427e9bcd4b851bd2e3d98aad0`, including the actual two-line
addition to existing CI path filters. The nine-file executable closure was
reconstructed from connected-provider reads and matched to Git blob IDs
before execution. No substitute compiler, trust generation or test fixture
was used. Execution was in an isolated cloud source subset, not a full
repository or provider-hosted CI run.

The retained behavior correctly keeps LIVE materialization blocked and every
nonempty LIVE requirement at OWNER_INPUT. Synthetic evidence binds exact
retained source, row, category and owner; generic capability cannot establish
sensitive proof. The review does not reopen those repaired predecessor issues.

## Demonstrated missing-input defect

A fictional pursuit with `requirements=[]` and `evidence=[]` was accepted even
when its pursuit ID was unknown to the retained generation. It yielded
`OWNER_REVIEW_READY`, an empty crosswalk, and no shortlist. Appending that empty
pursuit alongside the valid mechanics example left it invisible in the
readable crosswalk. Validation of each requirement cannot diagnose a pursuit
which supplies no requirements at all.

The repair requires a nonempty retained requirement list for each supplied
pursuit, reporting the exact input index in `InputError`. Validation completes
before output-directory creation, so the CLI exits 1 with a useful diagnostic
and no generated report for an empty pursuit. This applies to malformed LIVE
input too; the existing LIVE blocked-report behavior remains unchanged for
well-formed nonempty input.

An empty evidence list remains valid. Unknown nonempty pursuits remain
reportable as OWNER_INPUT. No qualification, company selection, contact,
submission or financial authority is added, and no original fixture is edited.

## Scope and interpretation limits

This compiler evaluates the caller's selected, supplied requirements; a
nonempty list is not proof that all requirements in an original solicitation
were captured. The manifest includes an R4 mechanics variant not selected in
the default fixture. The repair therefore does not insert every manifest row
or label a selected subset a complete solicitation inventory. A complete
inventory assertion still needs an explicit source-to-selection reconciliation
outside this bounded repair.

Likewise, OWNER_REVIEW_READY is the existing synthetic mechanics state, not a
commercial readiness, qualification, acceptance or approval statement. All
external authority fields remain false. The retained README and previous
recovery evidence are preserved rather than silently rewritten.

## Tests and source identities

Before repair, the exact published source passed its 25-method nested suite
normally and under real `python -O`; the three-method root bridge passed in
both modes. Additional empty-input cases then reproduced the defect.

After repair:

- 33 methods PASS in normal Python.
- 33 methods PASS under actual `python -O`.
- 33 methods PASS with ResourceWarning treated as error.
- Both three-method root-bridge runs PASS (normal and optimized).
- The 8 new methods against the original compiler produce 7 expected
  assertion/subtest failures; this is not a claim of 7 separate failing methods.
- All four original generated artifacts retain the exact SHA-256 values in
  RECOVERY_VALIDATION.md, asserted as constants by the new regression suite.

Each bridge itself runs the nested suite normally and optimized plus the real
CLI compile/verify round trip. Repeated executions are not additional unique
product tests. The bridge's declared nested count changes from 25 to 33 so the
existing battery actually accepts and checks the enlarged suite.

| Path | Repaired Git blob |
|---|---|
| compiler.py | `0482c7132240d2cad51f98d9222bdfa4c9d53bbd` |
| tests/test_empty_requirements.py | `29f250b2f97512f6abb95b22ef44fe8528d261b0` |
| ../../test_live_pursuit_partner_shortlist.py | `dfc7ed9b619b5f63cd67a1d13fb8f74dc144a50f` |

Original compiler: `e99388aa50ff7ac6276cd3799a92d05777cc679c`.
Original nested tests: `04c015431013f10897ae23d000aa1fd145273605`.
Original root bridge: `0246419192d74dec8e622d2b93992e71e7b38747`.
Retained trust generation: `0b2a7a851e8c564bd9d30ccee6530ad099089df2`.
Retained manifest: `2920d662b9dc13c49dc249cbcff667c06a61ca55`.
The fixture bindings remain those documented in RECOVERY_VALIDATION.md.

Environment: CPython 3.13.5, Linux x86_64. Commands from repository root:

```sh
python -m unittest discover -s revenue/live_pursuit_partner_shortlist/tests -v
python -O -m unittest discover -s revenue/live_pursuit_partner_shortlist/tests -v
python -W error::ResourceWarning -m unittest discover -s revenue/live_pursuit_partner_shortlist/tests -v
python -m unittest -v test_live_pursuit_partner_shortlist.py
python -O -m unittest -v test_live_pursuit_partner_shortlist.py
```

Observed output summaries:

```text
normal:    Ran 33 tests in 2.613s; OK
optimized: Ran 33 tests in 2.614s; OK
warnings:  Ran 33 tests in 2.828s; OK
root:      Ran 3 tests in 9.021s; OK
root -O:   Ran 3 tests in 8.769s; OK
negative:  Ran 8 tests in 1.712s; FAILED (failures=7)
```

The negative run used a separate copy of the original source with only the new
test file added. Main and the owner's branch were not changed by the reviewer.
The donor commit carries the complete code and tests for composition into the
existing carrier; its publication does not itself establish a main merge,
GitHub Actions success, or `swarm_review.py READY`.
