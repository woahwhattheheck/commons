# TITAN V3 S13 — top-leader route distillation

This experiment turns exact public top-five episode actions into executable, source-bound route arms instead of stopping at a schedule correlation report.

The incumbent complete-archive controller is called every turn, including turns where a leader arm emits the returned action. This preserves its private route/checkpoint state for immediate fail-closed handoff. No arm owns the opening day: all interventions begin at step 24. Three separations identify where any gain comes from: full action, market only, and farmer/hands only. Live hand count and unlocked-quadrant count must match the source replay at every owned turn; the first mismatch, absent tape row, or malformed action permanently returns the game to the incumbent.

The compiler consumes public replay JSON without importing competitor code. It binds every input by SHA-256, pairs each replay action with its pre-action observation, retains at least 700 actions per seat, selects the highest-reward witnessed route per exact team label, and emits deterministic compressed Python arms. The tournament is a funnel: a cheap both-seat Arlene screen over every arm, followed only by a mirrored Arlene/V1 panel for the top two strict survivors.

An arm advances only with nonzero returned-action activation, positive mean own cash, nonnegative median own cash, nonnegative global margin, zero new losses, and nonnegative own-cash and margin means in every opponent-by-seat stratum. Missing fields reject rather than silently weaken the gate.

This directory is analysis-only. It does not change the one-tree, canonical runtime, selected archive, configuration, provider, Kaggle submission, or release pointers.
