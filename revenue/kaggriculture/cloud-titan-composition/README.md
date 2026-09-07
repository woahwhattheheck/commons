# T08 standalone TITAN composition

Runnable research composition, owned by SORREL. No Kaggle submission or hosted-rating claim.

`controller.Titan(carrot=False, cap=False).act(observation, configuration)` owns
one Arlene instance per match. The carrot feature override is installed in that
instance's module. Frozen cap harvest wraps that same instance with
`one_way=True`, modifies verified free unit slots, and retains the original
market order sequence. This is hand-authored rule-policy composition, not an LM
or compressed model. Upstream definitions and attribution remain separate.

Independent callable arms live in `arms/`: baseline, carrot, cap, carrot_cap,
sell, flora, and carrot_sell. Each exports `agent(obs, configuration=None)`
except the exact upstream FLORA callable, which takes one observation argument.
The SELL arm includes its own intact Arlene. The carrot_sell arm replaces its
controller before any action with the carrot-patched Arlene; subsequent arrival
and cash projections use that same selected route. No cap or extra-hand actions
are passed into that unchanged-route projection.

Run `python build.py --arm carrot_cap --output artifacts/carrot-cap.tar.gz` to
produce a relocatable archive with root `main.py::agent`. Runtime uses only
Python standard-library dependencies and bundled deterministic mechanics; no
repository checkout, absolute VM path, installed model, or network is needed.
Archives contain vendor sources/notices, but no development game replays.

`benchmark.py` uses the existing cloud-eval evaluator unchanged and its pinned
official interpreter. Development seeds are 9780001, 9780019, 9780037, both seats
against independent Arlene and Apex controls. Held seeds 9780101 and 9780119
remain unused at this checkpoint. Outcome is terminal cash: W/T/L and paired
flips take priority; game-cash margin and own cash are distinct diagnostics.

Initial four-arm factorial: 48 completed games, zero failures. Baseline and
carrot: Arlene 1W/4T/1L, Apex 6W/0T/0L. Cap and carrot_cap have the same W/T/L,
with mean margin improvements over baseline of 17.17 against Arlene and 18.33
against Apex. Carrot produced no score difference on this development set.
This does not establish zero effect on other states. Frozen SELL and FLORA
control panels are in progress; no composition has been selected yet.

The frozen cap source's `run_cards.marginal_revenue` uses inventory+k at the
price floor. Preserved for an exact control; it is not the repaired SELL receipt
interface. Cap choice primarily ranks lost animal units, while its target-list
ordering uses that value. SELL uses the separately repaired floor-aware receipt
module. Both seats quote the same pre-commit inventory per marginal unit.

Generic post-production SELL integration was requested from its author. Cap
and extra-hand arrivals must be reconciled explicitly before combining with it.
No future shop draws, hidden seed, or evaluation-only opponent actions are live
policy inputs. Existing weaker branches remain reproducible as separate arms.
