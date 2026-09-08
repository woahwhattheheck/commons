# Methods-ready note — deterministic novelty world model

## Objective

ARC-AGI-3 evaluates agents that must learn unknown interactive environments rather than solve a static grid. A useful first milestone therefore needs to be more than random action selection while remaining generic enough not to hard-code public game solutions. This baseline treats each observation as a state in a small online transition graph and directs exploration toward actions that have historically produced visual novelty or level progress.

## Observation representation

The policy consumes only the public frame contract. If a response contains multiple 2-D frame arrays, the latest array is used. Grids are validated as rectangular, at most 64x64, and restricted to integer colors 0..15. The visual state key is a SHA-256-derived signature of the normalized grid. Available actions are normalized to the currently legal subset of ACTION1..ACTION7; the policy never intentionally emits an unavailable action.

This representation is intentionally lossless at the grid level. No semantic labels such as "player", "door", or "goal" are assumed before interaction evidence exists.

## Transition learning

For each state/action pair the agent records visits, successor states, changed-cell counts, novel successors, and level advances. A transition receives a small penalty when the display is unchanged, positive reward when visible state changes, an additional novelty bonus when a previously unseen state is reached, and a much larger bonus when `levels_completed` increases.

When a state is revisited, actions are ranked by a deterministic upper-confidence score combining mean observed transition reward with an exploration term. Untried legal actions receive first priority. This produces a reproducible explore/exploit schedule without random seeds and gives the harness concrete diagnostics for every decision.

## Coordinate action

ACTION6 requires coordinates but the API does not identify active click regions. Candidate coordinates are generated without privileged information: first from the centroid and a bounded sample of cells that changed since the prior frame, then from centers of non-background connected components, then from the grid center and corners. Candidate visits are tracked per state so repeated coordinate exploration walks through distinct salient points before repeating them. Coordinates are always clamped to the official 0..63 range.

## Reset and termination

The organizer specifies that GAME_OVER accepts RESET only. The policy therefore emits RESET immediately for NOT_PLAYED or GAME_OVER states and the official adapter terminates on WIN. Episode-pending state is cleared on reset while accumulated transition evidence is retained, allowing retries to benefit from prior exploration.

## Reproducibility

The core is Python standard library only and deterministic for an identical observation/action sequence. The official adapter is intentionally thin and pinned to the public ARC-AGI-3 Agents interface. Synthetic unit tests cover frame validation, current-action constraints, deterministic exploration order, coordinate selection and bounds, transition reward, level-progress reward, diagnostics serialization, and repeatability.

## Limitations and planned ablations

Novelty is not the same as task progress. Environments with reversible visual effects can attract an explorer even when they do not help win, and the state hash does not yet abstract equivalent configurations. The next empirical work should therefore measure: (1) novelty-only versus novelty+level reward, (2) full-grid identity versus object-centric state abstraction, (3) one-step UCB versus learned multi-step planning on the recorded transition graph, and (4) coordinate salience heuristics versus uniform coordinate sweeps. Any improvement should be accepted only on reproducible public/local ARC runs, not on synthetic fixtures alone.

No leaderboard, milestone placement, submission, or award is claimed in this note.
