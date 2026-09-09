# TITAN V3 active-prefix seed-funding dependency certificate

Operation: `titan-v3-seed-prefix-dependency-20260909-01`  
Owner: `SOL-PARALLAX`  
Exact branch base: `e2b99bb417675ad574aa4d12cf1c32e5795124c5`  
Slack claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788985395120849

## Finding

The current `TitanAgent._seed_selected` has two different notions of the market
queue boundary:

1. `SeedBudget.apply` receives `maxMarketOrdersPerTurn`, so its proposed seed
   edits are constrained to the executable prefix.
2. The following dependency predicate scans `selected["market"][edit + 1:]`
   through the entire serialized tail.

The official interpreter first truncates every player queue to
`q[:maxMarketOrdersPerTurn]` and only then parses or executes orders. A capital
order after that boundary cannot consume cash, create a hand, unlock land, buy a
product, or buy an animal. Treating it as an executable downstream dependency
can nevertheless route an otherwise demand-valid seed reduction into the
conservative funding selector and restore the original overbuy.

The source-bound discriminator uses a ten-order cap, current cash `$10`, active
slot 0 `BUY_SEED WHEAT 2`, and inactive slot 10 `HIRE`. The current predecessor
returns the baseline because the active seed request costs `$20`; exact official
market execution then buys one unnecessary seed and leaves `$0`. The candidate
returns the already-computed demand-valid proposal; the inactive HIRE remains
unexecuted and cash remains `$10`. This proves a current-turn semantic and cash
difference. It is not a whole-game or leaderboard claim.

## Candidate behavior

`seed_prefix_dependency.py` installs an instance-local wrapper around the exact
current `_seed_selected` method. It does not call a producer or controller and
does not replace the seed budget, selected action, route, unit projection, or
canonical funding module.

The source-bound instance wrapper executes the exact current method body once
and adds one admitted branch immediately after the existing `SeedBudget.apply`
call. It reuses that already-computed proposal—never calling the seed budget,
producer, or controller a second time—and bypasses the funding selector **only**
when all of the following are proven:

- baseline and proposal are mappings with equal-length market queues;
- all non-market action fields are byte-equivalent as Python values;
- every changed slot is inside the official executable prefix;
- every edit is a strict same-product `BUY_SEED` quantity reduction or removal;
- no `HIRE`, `BUY_LAND`, `BUY_PRODUCT`, or `BUY_ANIMAL` follows an edit inside
  the executable prefix; and
- at least one such apparent dependency exists only in the inactive tail.

Every malformed input, source drift, active dependency, non-seed change,
quantity increase, edit outside the cap, missing selector, or broader action
mutation delegates to the canonical behavior or leaves the agent untouched. The
exact funding-module object is restored in `finally`, including exceptions.
Installation is match-instance local, idempotent, reversible, and source-hash
bound to current runtime Git blob `b952c9c228ecbde592bf3d2df01638677abb0d24` and method SHA-256
`b3bf094820b77a7b871b017c78fdfa18ef3663c94970c96c2eb572e5c693ff01`.

`candidate_main.py::agent` is a panel-ready source-tree entrypoint. It loads a
private copy of canonical `main.py`, wraps only that module's `_new_instance`
factory, and delegates every action to the unchanged canonical `agent()`—so
singleton, reset, cold-start, fallback, and deadline semantics remain owned by
current main. It derives stripped-worker module paths from the canonical builder
instead of maintaining a second dependency map.

## Verification

From this directory:

```bash
python -m py_compile seed_prefix_dependency.py candidate_main.py seed_prefix_test_support.py \
  test_prefix_classification.py test_installer.py test_exact_current.py
python -m unittest -v test_prefix_classification.py test_installer.py test_exact_current.py
```

The suite contains 21 methods:

- 17 pure/installer contracts, including a deterministic 1,000-queue adversarial
  classification corpus;
- exact source binding against current `TitanAgent._seed_selected`;
- predecessor-versus-candidate execution through the actual current method and
  actual `seed_funding.py`;
- an active-prefix capital countercase that remains fail-closed; and
- exact official `_process_market` execution proving slot 10 is inert under a
  ten-order cap and reconciling the `$10` cash difference.

The local connector worker completed the 17 source-independent methods in
under 0.1 seconds with zero failures/errors; the four repository-bound methods were
skipped only because the connector worker has no GitHub filesystem checkout.
The pull-request workflow checks out the immutable PR head and requires all 21
methods against repository source. `RESULTS.json` records exact identities and
will not treat a skipped exact-source test as hosted evidence.

## Integration packet

`install.patch` shows the minimal direct canonical repair: derive the order cap
once and bound the downstream dependency scan to `edit + 1 : limit`. It is a
review artifact only and is not applied by this candidate. Canonical runtime,
configuration, builder, current archive, source pointer, exports, S02, and every
peer-owned candidate remain unchanged.

## Disposition

`SOURCE_CANDIDATE / LOCAL_TESTED / EXACT_CURRENT_CI_PENDING / GAME_UNMEASURED`.

No Kaggle/provider action, submission, score claim, hidden rival state, future
cash forecast, or default enablement is included. Gameplay admission requires an
immutable exact-head both-seat panel and owner review after the source contracts
pass.
