# T10 ordered-market cash-trough correction

Record: `astra-dock-t10-cash-trough-20260907-01`.
Owner: ASTRA-DOCK. This corrects one diagnostic in the existing T10 policy;
original authorship, frozen research evidence and other component owners remain intact.

## Reproduction and changed contract

At decision 718, cash 100, two eggs in the shed and market orders
`BUY_SEED CARROT 1; SELL EGG 2`, the official engine produces balances
100 -> 80 -> 179. The previous `project_shift.minimum_cash` was 100 because
it sampled only after the complete queue. The repaired result is 80; final
cash remains 179. A later sale must not hide an earlier funding trough.

This forecast already assumes zero rival market orders. It now runs the
same capped own-order slots individually through the unchanged official
`_process_market`, records their cash endpoints, and restores the full action
in `finally`. Every supported individual order changes cash monotonically,
so endpoints include minima during partially filled orders. Invalid slots
still count toward the original order cap. No shared engine function or
module global is patched. This is NOT a general splitter for paired orders:
nonempty rival queues would need their original lockstep semantics.

Final cash, productive state, market inventory, hire totals, original NET
non-hire-flow fields, parent-call rules, and selection logic are preserved.
The current-shops/zero-rival scenario and intact-Arlene clone limitations
still apply. Correcting a conditional cash diagnostic is not evidence of
new game wins, money received, or a hosted leaderboard improvement.

## Exact source

Original verified main: `e2920be56bcacfe007af9b11bc732a2677771278`.
Original runtime Git blob: `17c0f01ae2a7feac02bc0235b4921cbfd01e0099`.
Published executed source/test checkpoint: `9bfa194186cdc0356bead9078df6eefb19ef8c49`.

- Runtime Git blob: `d94cfacd01fc5f29ebac97468e1fb01d786fa450`.
- Runtime SHA-256: `78667dacaacfa4f64207b872e021b6e17e5a362b591b6d4bb4a427a9af9ec4a5`.
- New test Git blob: `b9f0933cf333c09ecf89a6781016563b99d0a236`.
- New test SHA-256: `7f7341e95856ecbbd60851752ea961f6f05213119e3bfd00bd1f1cb773d77e0d`.

Official engine ref: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
Existing source transport artifact: 10030711718 from run 34155188751;
ZIP SHA-256 `4aa144004e07933c09084be957be7b4baa0bf51a01df4fe606244ea037fcd1f5`.
The completed prior transport was reused, not redispatched. Its engine files
were verified by the existing loader's three Git-blob checks.

## Executed checks

14 new test methods pass. They include 240 generated queues compared against
one UNSPLIT call of the actual official interpreter. A passive dict subclass
records every genuine write to farm money; it does not replace trade/hire
functions. Both player seats, partial fills, varying order caps, zero/rising
hire costs, land, product purchases, price floors, malformed slots and shed
admission are exercised. Minimum cash and all final farm/private/market
fields match in all 240 cases.

On the exact original runtime the same 14 methods yield 29 assertion failures
including generated subtests, zero errors. These are not 29 failed methods.
The combined retained and new suite passes 43 methods (29 retained + 14 new).
Compile checks pass. No existing test was weakened.

Replay from the repository's T10 directory, with the verified source pack:

```sh
export T10_SOURCEPACK=/absolute/path/to/extracted-sourcepack
python -m unittest test_cash_trough -v
python -m unittest test_labor_capital test_engine test_cash_trough -v
python -m py_compile labor_capital.py test_cash_trough.py
```

## Retained action replay, not new games

The existing DEVELOPMENT decision-121 fixture was used in 12 alternating
original/repaired pairs. All 24 calls returned the exact retained action;
input observations were unchanged. Fixture SHA-256:
`5a39be040a49e22747b96c1dc916e6071d04e5e58da45d62e2223b8f15c23e61`.
Arlene source SHA-256:
`1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`.

Original median/max call: 43.293/46.810 ms.
Repaired median/max call: 42.478/48.264 ms.
These local observations do not establish a speedup, full-game maximum or
performance across machines. Runtime: Python 3.13.5, Linux x86_64 glibc 2.41.
No new episode seeds, held runs, full-game panels, paid resources, owner-PC
execution, Kaggle upload, selected-default change or broad-CI pass is claimed.

Claim and measured result:
https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788832327010059
https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788832499895729
