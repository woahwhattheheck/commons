# Independent audit — merged S02 public-surrogate planner

Operation: `titan-v3-s02-admission-firewall-20260909-solpro`

## Reviewed identity

- Target PR: `woahwhattheheck/commons#11223`
- Merge: `db7f1a1e6581388de1170942858c50b1b525fc19`
- Planner blob: `aea58ca09d705db39202e1bfa1dd789cde01f929`
- Historical archive used by the experiment: `f8f1750266b3cfaea0ebfe663f287aa9c5a2682f6fc47bc932957e1d48e63f1c`
- Fresh inspection main: `3379fd799766609691b4bb777e13f7b3cae0da00`
- Fresh canonical archive at inspection: `a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba`, 423575 bytes, 107 files
- Fresh canonical source manifest: `b96676977687ee8a92d7213380f96bf5774a5ec26925cb4f0d66bdd244eb44ba`
- Official engine ref named by S02: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`

The target planner blob was unchanged on fresh inspection main.

## Disposition

**BLOCK EXECUTION / KEEP EXPERIMENTAL.** This is not a request to delete the
research path. It is a source-level finding that the merged H=6 mechanism does
not implement the stated receding-horizon contract and cannot be admitted into
canonical TITAN from its current evidence.

## Findings

### S02-F1 — candidate policy is replaced by PASS after transition zero (critical)

`rollout()` executes `own_action` only when `t == 0`; every later simulated own
action is `legal_pass(own_obs)`. The model therefore measures one action plus an
artificially idle farm, not “commit one action and replan” under a faithful
canonical continuation. Productive purchases, route obligations, servicing,
harvest, deposit, and sale are stranded by construction.

This directly violates the S02 order’s explicit requirements to preserve
funding/route obligations and reject short-horizon liquidation that strands
production.

### S02-F2 — score collapses algebraically to worst absolute cash (critical)

The evaluator computes:

```text
mean = average(cashes)
down = min(cashes)
score = mean - max(0, mean - down)
```

Because `down <= mean`, this is exactly `score = down`. It is not paired regret
against the canonical action, and it assigns no value to non-cash productive
state. Combined with S02-F1, deleting investment or harvesting less can look
better simply because the simulated farm never completes the corresponding
production path.

### S02-F3 — candidate generator destroys canonical intent (critical)

The candidate family may:

- append or delete `HIRE`;
- delete, halve, or drop the last `SELL`;
- replace `HARVEST` with `PASS` or vice versa; and
- truncate the final market row.

There is no obligation, acquisition, route, inventory, or terminal-realizability
certificate around those edits. The candidate family therefore violates the
order’s “canonical-compatible macros” and “preserve funding and route
obligations” boundary before scoring begins.

### S02-F4 — the “repeat” rival is permanently PASS (high)

`self.last_rival` is never populated from an observed rival action. At the end
of every turn it is assigned `legal_pass(obs)`. The “repeat” scenario therefore
repeats a synthetic PASS, not an incumbent response.

### S02-F5 — unseen rival private state is silently fabricated empty (high)

`instantiate_state()` substitutes `_new_private()` for the rival. That means
zero rival shed, seeds, and carried inventories. This is a sensitivity model,
not the live hidden state, but the code treats it as a scoring world without an
uncertainty barrier. The first S02 lane had already established that the live
observation does not contain the rival private packet needed for faithful exact
reacting transitions.

### S02-F6 — a mutable rival TITAN shadow is reused across candidates (high)

`Planner._shadow()` constructs one stateful agent and stores it on the planner.
Candidate/scenario evaluation calls that shared object in iteration order.
Earlier simulations may therefore mutate history/controller state used by later
candidate scores. Candidate comparison is not sibling-isolated.

### S02-F7 — hidden future RNG is replaced by an arbitrary seed (high)

The simulated environment uses `configuration.seed` when present, otherwise
zero. The live S02 thread already records that real H24 continuations cross
hidden end-of-day RNG. An arbitrary future seed cannot support an exact live
execution claim.

### S02-F8 — tests do not exercise the mechanism (high)

The merged test file has two tests: one confirms a generated HIRE variant exists
and one confirms the disable flag returns canonical. It does not test exact
transition behavior, candidate sibling isolation, hidden-state boundaries,
route/funding preservation, baseline-relative scoring, deadline subset bias,
or the observed catastrophic regression.

## Observed result check

The supplied `s02_observed_smoke.jsonl` transcribes the merged PR’s four matched
Arlene rows. `validate_panel.py --schedule S02-OBSERVED-SCHEDULE.json --min-pairs 4` produces:

- baseline: 4W / 0T / 0L;
- S02 H=6: 0W / 0T / 4L;
- mean paired margin delta: `-90047.5`;
- worst paired margin delta: `-110292.0`;
- verdict: `admitted=false`.

This is a smoke rejection, not a population estimate. It is already sufficient
to prohibit promotion of the tested H=6 bytes.

## Corrective design in this packet

The replacement is a conservative admission firewall:

- shadow-only by default;
- exact canonical fallback on every uncertainty/error/deadline path;
- worker actions immutable;
- all non-market fields plus market row payloads, quantities, multiplicity,
  and empty-row multiplicity immutable;
- candidate family limited to exact queue permutations;
- collision-free typed canonicalization for action and post-state identity;
- fresh engine state for each baseline/candidate/scenario sibling;
- identical deterministic pair seed with global RNG state restored;
- exactly one modeled transition, honestly labeled;
- bounded, uniquely named scenario enumeration;
- live rival-private/end-of-day-RNG visibility certificate;
- empty-rival worlds explicitly sensitivity-only, never exact evidence;
- strict post-state equivalence apart from own cash;
- paired cash delta, not absolute cash;
- complete exact scenario count and minimum gain required for execution; and
- machine-readable full-game panel gate bound to an explicit expected key set.

The built-in runtime exposes one conservative PASS/empty-private sensitivity
scenario and labels it non-exact. Therefore the unintegrated replacement cannot
silently change gameplay even if someone sets `TITAN_MPC_MODE=execute`; it
returns canonical unless an owner supplies a source-bound evidence mechanism
and validates it through exact-current full-game panels.
