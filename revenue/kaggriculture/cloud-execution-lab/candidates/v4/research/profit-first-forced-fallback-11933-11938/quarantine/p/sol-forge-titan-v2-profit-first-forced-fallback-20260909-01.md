# SOL-FORGE — TITAN V2 profit-first forced fallback

- Operation: `titan-v2-profit-first-forced-fallback-20260909-sol-forge-01`
- Claim receipt: Slack `#titan-kaggriculture`, message timestamp
  `1788994611.162249`
- Review receipt: PR `#11799`, review `5160721101`
- Exact starting commit:
  `14ca164eda154e4d17d10480518d64b7908eb45b`
- Branch: `sol-forge/titan-v2-profit-first-forced-fallback-20260909-01`

## Owned paths

- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-profit-first-forced-fallback-sol-forge/**`
- `.github/workflows/titan-v2-profit-first-forced-fallback-sol-forge.yml`
- `p/sol-forge-titan-v2-profit-first-forced-fallback-20260909-01.md`

## Hypothesis

Frozen V2's selector admits feasibility repairs correctly but ranks the Boolean
`forced_feasibility` flag before robust gain.  A negative forced candidate can
therefore displace a positive ordinary candidate.  The strict KEEL ablation
removes both that priority and the fallback admission, so it cannot attribute a
score effect to priority alone and can preserve a known-infeasible reference in
an all-forced/no-positive state.

The owned arm preserves eligibility and changes only the rank from
`(forced_feasibility, gain)` to `(gain > 0, gain)`.  This admits the highest
positive robust gain first and retains the highest-valued forced plan only when
no positive plan exists.

## Acceptance

1. Exact materialization changes only copied `scheduler.py` and retains every
   named V2 semantic marker, including forced admission.
2. Real-scheduler mixed and forced-only witnesses distinguish frozen V2,
   strict KEEL, and this priority-only arm.
3. All delegated custody helpers match their recorded Git blobs and bind to
   this operation.
4. Hosted execution uses exact frozen V2 control, exact official engine and
   evaluator identities, four literal seeds, V1 and public Arlene opponents,
   both seats, and the complete 720/719 lifecycle.
5. Classification uses candidate-only pre-interpreter action digests and
   requires nonnegative mean own-cash delta in every opponent and
   opponent-by-seat subgroup for an upside verdict.
6. Frozen/canonical/runtime/config/archive/pointer/provider/Kaggle paths remain
   untouched and `build_integrated.py --check` passes.

## Claim boundary

No leaderboard, score, promotion, merge, or submission claim is made before the
exact hosted artifact is read back.  A non-green hosted result remains useful
causal evidence and must not be relabeled as a win.
