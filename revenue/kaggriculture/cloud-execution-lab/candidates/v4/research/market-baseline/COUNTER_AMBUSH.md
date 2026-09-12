# TITAN V4 COMEBACK — counter-ambush market economics

**Disposition:** research-only, default-neutral, no decision authority.

This package evaluates two adversarial ideas from the externally reported Apex V7 sell schedule without creating a second seller/controller: (1) sell one callback before a known rival dump, and (2) buy fertilizer after a rival fertilizer dump. The reported schedule is **not authenticated opponent source** here. It remains metadata until the metagame owner supplies a retrievable artifact/byte identity.

Reported external schedule: MELON 249; STRAWBERRY 381/403/499; FERTILIZER 522.

## Official-engine boundary

Pinned engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

The oracle mirrors only source-proved mechanics needed by the counterfactuals: per-unit market pricing, the $1 SELL supply-floor exception, BUY_PRODUCT post-buy quoting and inventory decrement, FERTILIZE's three-day active window, fertilizer's +1 production bonus on qualifying production events, and callback ordering UNIT -> MARKET -> TOWN. The optional verifier fail-closes on the exact engine blob plus those source anchors.

## Strawberry pre-dump correction

The naive instruction “sell Strawberry at 380 before Apex 381” omits town consumption. Step 380 is divisible by four, so each already-unlocked Strawberry-consuming shop drains one Strawberry after our market stage and before the step-381 rival market stage. At most eight relevant shop instances can exist. That town drain partially reverses our intentional market glut before the rival arrives.

Synthetic boundary, deliberately **not** an Apex quantity claim: starting market inventory 10,000, our sale 10, rival sale 10.

- step 380 with eight Strawberry-consuming shops: town drain 8, own early-vs-late gain $38, rival suppression $261, gross relative-margin swing $299.
- step 402 with no shop drain: own timing gain $192, rival suppression $192, gross relative-margin swing $384.

The general mechanism is real, but the best t-1 callback depends on the current public unlocked-shop multiset and current market inventory. Do not hardcode 380 merely from the rival schedule.

## Fertilizer sponge correction

A rival fertilizer dump can create a real purchase discount because successful sales increase market inventory and subsequent BUY_PRODUCT units quote at post-buy inventory. But buying discounted fertilizer is not automatically profitable.

Synthetic boundary: market inventory 10,000, rival dumps 40 fertilizer, we buy 10 next callback.

- buy cost after dump: $931
- buy cost without dump: $1,011
- opponent-created discount: $80
- source-max WHEAT bonus: 2 extra crop units per fertilizer
- gross WHEAT sale-price threshold to cover fertilizer alone: $47/unit
- at base WHEAT $25, source-max 20 extra units are worth only $500 gross, below the $931 fertilizer cost before labor, movement, shed pressure, clipping, or sale timing.

BUY_PRODUCT lands fertilizer in the shed during MARKET after UNIT. Best case is therefore BUY at 523, PICKUP at 524, FERTILIZE at 525; movement pushes that later. Runtime fertilizer owners should require live crop value and logistics to clear this admission threshold rather than treating a rival dump as free value.

## Validation

Authoring container:
- `python test_counter_ambush.py`: 12/12 PASS
- `python -O test_counter_ambush.py`: 12/12 PASS
- `py_compile`: PASS

The full-checkout exact-engine verifier was not executed in the authoring container because the repository checkout was unavailable there. Official engine bytes/source were independently inspected through the GitHub connector. No current-native games, official-engine games, economic-gain claim, hosted-CI-green claim, runtime activation, config/default/archive/workflow/evaluator/Kaggle/submission mutation, or opponent-schedule authentication is claimed.

## Handoff

SELLWINDOW / CRASH / TOWNCLOCK retain sale timing and scheduling. FERTWARE / FERTDEADLINE / HERDSCALE retain fertilizer runtime/service policy. ORDERBUDGET retains market-row capacity. This package supplies only counterfactual economics and admission/falsification evidence for those existing V4 lanes.
