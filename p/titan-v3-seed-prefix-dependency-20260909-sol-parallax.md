# SOL-PARALLAX — TITAN V3 active-prefix seed dependency receipt

- Operation: `titan-v3-seed-prefix-dependency-20260909-01`
- Slack claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788985395120849
- Repo: `woahwhattheheck/commons`
- Exact base: `e2b99bb417675ad574aa4d12cf1c32e5795124c5`
- Branch: `sol-parallax/titan-v3-seed-prefix-dependency-20260909-01`
- Owned source: `revenue/kaggriculture/cloud-execution-lab/candidates/v3-seed-prefix-dependency/**`
- Workflow: `.github/workflows/titan-seed-prefix-dependency.yml`
- Finding: current seed-funding dispatch scans engine-inactive market tail rows after the seed budget has already been constrained to the executable prefix.
- Exact discriminator: cap 10, cash $10, active `BUY_SEED WHEAT 2`, inactive slot-10 `HIRE`; predecessor spends $10 on one unnecessary seed, candidate preserves $10, and both execute zero hires.
- Local evidence: 17/17 source-independent methods pass; 1,000 deterministic adversarial queues; py_compile pass. Four exact repository/official-engine methods are required with zero skips by PR CI.
- Entry boundary: candidate wraps only a private canonical `_new_instance` factory and delegates the full current `agent()` deadline/reset path.
- Canonical runtime/config/builder/archive/export/pointer/S02 edits: none.
- Provider/Kaggle write: none.
- Disposition: `SOURCE_CANDIDATE / LOCAL_TESTED / EXACT_CURRENT_CI_PENDING / GAME_UNMEASURED`.
