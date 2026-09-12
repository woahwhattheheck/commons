# Selective age-three carrot production

This executable V5 experiment changes wheat plantings to carrots only when the existing route waters and harvests an equal-sized living crop on age three, visible town demand supports the added carrot supply, and a full extra carrot seed plus replacement wheat can be funded. It adds no worker travel or hires. The original V4 archive remains the control.

The production census found many three-unit age-three wheat lots in submitted V4. Age-four wheat sites are ineligible because carrots expire sooner. Sites whose harvester feeds the wheat directly before depositing it also remain wheat: buying into the shed cannot replace carried feed. Existing fertilized sites and the singleton crop_release preparation are excluded.

The economic screen uses current shops with duplicate demand, sale-before-town event ordering, the engine's rounded nonlinear quotes, both farms' visible carrot plants at full lot capacity, and already committed candidate supply. It discounts projected carrot receipts to80%, charges all lost wheat at replacement-buy prices, charges the full additional20 carrot-seed cost, and requires at least12 remaining. Maximum four active candidate lots. These are conditional forecasts, not guaranteed future prices.

The seed is bought before the proposed planting and confirmed from actual next-observation inventory. All same-turn CARROT and WHEAT seed demands must be fundable before a swap. At harvest, the candidate purchases the displaced wheat; extra carrot sales are bounded by current post-unit shed inventory. Actual returned actions bind the state, including canonical deadline fallback. Unit changes precede the existing seller's post-unit snapshot; additional market orders enter after existing market guards. Existing features and operating purchases stay enabled.

## Measured evidence

`REPLAY-RESULTS.json` contains eleven complete recorded-action continuations, including six new losses downloaded after the candidate was developed. All7,909 baseline transitions match the official replay's farms, markets, towns, and private state. Three cases improve relative final cash: Sian+1512, William+2676, refine123+3601. Eight cases make no action change. Final own farm tiles match the control in all eleven cases. Each engaged case buys/plants10 carrot lots, harvests/sells30 additional carrots, and purchases30 replacement wheat. These are causal replay diagnostics with recorded opponents, not adaptive wins or a rating forecast.

The preceding v2 wrapper completed one fresh local full-policy comparison against Arlene on seed2051966578/seat0: control82908–93396; candidate83462–92963, relative delta+987. Both finished719 decisions. Windows deadline reconstruction differed (control97 unavailable instance diagnostics, candidate121), so this single development comparison is not clean promotion evidence. V3 avoids building a future schedule on callbacks with no next-turn wheat planting. The current package passed7 focused strategy tests and an import/two-decision engine smoke. Use the Linux panel below for the current source.

## Reproduce

Exact submitted V4 control is submission56182437, archive SHA256 `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`. It is attached to the [regression handoff](https://tokenjunkielabs.slack.com/archives/C0C1F274SGH/p1789208972111539). The experiment has77 archive members: original main.py is preserved as baseline_main.py; the wrapper and selective_carrot.py are the only added implementation.

```bash
python build.py --baseline /path/to/titan-v4.tar.gz --out /tmp/carrot-candidate --tar /tmp/carrot-candidate.tar.gz
python -m unittest discover -s . -p test_selective_carrot.py
python paired.py --kg-root /workspace/commons/revenue/kaggriculture --engine-dir /path/to/pinned-engine --baseline /path/to/titan-v4.tar.gz --candidate-dir /tmp/carrot-candidate --output /workspace/carrot-pairs --seeds 2051966578,1209125501 --opponents apex_v7,arlene_v14 --seats 0,1
```

The launcher reuses the existing process-isolated official-engine evaluator and pinned opponent bank. Eight matched pairs/sixteen games, alternating arm order, fresh processes and private directories. Seed1209125501 is a fresh holdout. It records exact member/engine/opponent identities, actual carrot planting events, failures and paired scores. It does not submit to Kaggle. Keep numerical output in #sim-data; merge the experiment infrastructure without changing the production default.

Source basis: official engine blob `3c202c7ee921da239356789e266b694635103fc4`; exact V4 source `4af1113154e78c662780e6658cd920daac7902e3`; original crop-release lifecycle; WF1's leader production census; new official V4 losses and leader episode108115160. No hidden opponent inventory, future shops, or replay actions are available to the competition policy. Local replay-probe fixtures are diagnostic harnesses only and are not packaged into the agent.
