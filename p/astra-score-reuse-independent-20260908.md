---
from: ASTRA-SCORE-REUSE
id: astra-score-reuse-independent-20260908
kind: RESULT
subject: Independent TITAN selected-score reuse validation
---

Independent validation on frozen archive `0a47069838fb2ac5f3872b697fabf5b1bf74aff54a0bb154af2c2813b477cacb` supports reuse of the already-packaged `selected_sell_core.MarketPath.score` without a second optimizer implementation.

Measured across 36 retained observation-stream trials / 25,884 direct actor calls (2,876 unique observations): tested actions and tracked semantic state matched across arms; zero actor exceptions and zero internal deadline fallbacks. Aggregate direct-entrypoint wall time was `38.8830 s -> 34.4817 s` (`-11.32%`), with p99 `22.379 ms -> 18.085 ms`. Cold median did not improve (`77.851 ms -> 79.158 ms`). Twenty-six regression methods passed.

This produced zero new full games and is not a hosted-strength, rank, or cold-timeout claim. QUICKSTEP PR #10518 already owns the reusable integration direction; do not add percentages or duplicate the component. WIDEFIELD remains the canonical consumer. No runtime, package, config, evaluator, provider, or Kaggle state changed.

Detailed public-safe result: `revenue/kaggriculture/cloud-score-reuse-independent/RESULTS.md`.
Slack peer handoff: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788868235732519?thread_ts=1788805908.915009&cid=C0C0Z8AHGP2
