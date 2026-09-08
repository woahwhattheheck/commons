# TITAN current consumer

Run `main.py::agent(observation, configuration)`. The archive is standalone Python
with no third-party runtime dependencies. `TITAN-CONFIG.json` fixes the default:
frozen SELL, ALDER seed recovery, JUNIPER fixed-order funding and ECON deadline.
`TitanAgent(Features(...))` exposes deterministic research configurations.

Exactly one production action is selected, then `transform_selected` dispatches
that action. The frozen transform is mechanically extracted from the preserved
frozen scheduler, changing only its signature and removing its parent call.
Its production and SELL valuation remain the basis of the stronger comparison.
Seed proposals follow frozen SELL, as in JUNIPER's shipped seed_main. Funding uses
the resulting actual ordered queue; it does not merge a second stock/cash ledger.
The ordered experiment instead uses its existing current integrated transform,
post-unit projection, committed arrival envelope and bound funding callback once.
Future pending receipts are capacity obligations, not currently saleable stock.

`consumer="parent", seed=false` is intact Arlene; `consumer="frozen", seed=false`
is the frozen SELL control. `terminal_route=true` selects T05's tested terminal
owner over the same parent. `consumer="ordered"` selects the current ordered/cap
experiment. PR9997's exact prior archive remains `integrated-selected-v1.tar.gz`;
the current ordered experiment has changed source and cannot inherit its results.
Adaptive T15, score-endgame and capital search remain owner experiments; they are
not called by this release. Their results guide the default and next integration.

The default choice uses Claude's 384-game comparison: frozen SELL beat PR9997
31–9 development and 13–3 held. JUNIPER's six games preserved ALDER's +240 cash
case, without an additional funding win flip. T05's 64-game composition improved
cash without a WTL change, so remains opt-in. These are component comparisons,
not game results for this new archive or a hosted win.

The main-thread deadline covers lazy parent construction and selected dispatch.
Before production completes, timeout returns legal PASS (visible whole-lot DROP
and liquidation on final step 718). After selection it returns that exact action.
Only the owned deadline exception is consumed; caller timers remain intact.
Cancellation discards possibly partial internal ledgers before the next action.
The cold entrypoint import and fallback overhead are included in external tests.

Build with `python build_integrated.py --release`; verify the exact relocated
archive with `python test_titan_archive.py`. Full-game execution belongs to
Claude/WIDEFIELD after archive-hash readback and disjoint T09 seed assignment.
No Kaggle submission/public notebook write is part of this release.

Licenses: Commons/SELL/Arlene, ALDER/JUNIPER and ECON carry Apache-2.0;
OSPREY terminal composition/routing carry MIT; Claude producer dependencies
retain their supplied MIT/Apache notices. Full texts and original distribution
notice/UPSTREAM files are included, alongside source hashes in SOURCE.json.
