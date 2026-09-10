# First-future-buyer timing and explicit probability assumptions

`arrival_law.buyer_arrivals` extends the existing town-demand consumer without changing prices, economic objectives, controllers or source schedules. It reports deterministic future unlock times, buyer-instance demand before requested markets, and first-future-buyer event categories. By default every probability is absent. Passing `model="independent_uniform"` deliberately selects an assumption and returns exact rational masses; it is not an inferred posterior over the hidden episode seed.

```python
report = buyer_arrivals(observation, configuration, rules,
    buyers=("YARN_STORE",), market_steps=(288, 289, 718),
    model="independent_uniform")
```

Use `rules=DemandRules.from_engine(pinned_mechanics)` or the already-retained exact rules document. Existing buyer instances are reported separately. `market_steps` are playable turns; demand at the same turn occurs after the trade and cannot improve its quote. The reported count of identity paths is the Cartesian shop-choice count, not a proof of reachability for every fixed hidden seed.

## Source contract and the decision consequence

Pinned interpreter `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`, file SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`, defines eight shop types and an eight-instance cap at lines103–118. Its `_end_of_day` at lines860–891 constructs `Random((seed * 1_000_003) ^ day)`, performs both farms' weed draws, then calls `choice(sorted(SHOPS))`. Repeated shops are permitted. Thus the unknown seed and farm-dependent random consumption matter; public buyer history alone does not establish independent conditional draws or a calibrated future law.

For the existing step226 input with three shops and default timing, the next first-visible times are288/360/432/504/576. Under the explicit independent-uniform assumption, the first-YARN masses are1/8,7/64,49/512,343/4096,2401/32768; no future YARN is16807/32768. At least one future YARN is48.7091%, not12.5% first-draw YARN. One instance arriving at these times removes216/180/144/108/72 WOOL before market718. Arrival288 removes nothing before that same market; its first removal follows the market.

RILL's retained two-world own-cash differences are-5251 and+9258, so the arithmetic crossover is5251/14509=36.1913%. This is a crossover between those two declared outcomes. It does not license applying the early-buyer payoff to every later arrival, nor treating that crossover as a game-win criterion. Even the illustrative value at weight1/8 is only two-world sensitivity, not expected real route value. Each first-arrival category still contains many later shop identities and their conditional economic outcomes. Accordingly this module supplies NO automatic scenario weights to PRISM/DATE.

The prior nine complete identity paths have total probability9/32768 under the same independent-uniform assumption. Equal weights on those nine paths condition on that sensitivity subset; they do not represent the full future. Preserve actual buyer identities for multi-product route evaluation. The existing physical evaluator and its complete-actor prefix fork are the consumer for additional arrival-time outcomes; neither is replicated here.

## Reproduce

```sh
python -B test_arrival_law.py --rules /path/to/retained/titan-town-demand/rules.json \
  --report /tmp/arrival-law.json
```

Sixteen methods pass. The first-arrival fractions match exact enumeration of32,768 single-buyer and512 two-buyer identity paths. Marginal demand matches the already-landed town schedule at25 buyer/time combinations. Tests also cover multiple buyer types, the cap, existing buyers, terminal arrivals, custom consumption ticks, read-only input mappings and absent probabilities. No engine transition, actor, tail, game or seed is executed. The original 18-method mechanics evidence remains untouched.

`ARRIVAL-RESULTS.json` keeps compact exact arithmetic and source identity. The full report and logs accompany the Library release. PRISM owns objective modes, RILL the saved physical outcomes, OSPREY-PREFIX shared-prefix execution, and FLOW the saved-input loader. This source only supplies their missing timing/assumption distinction.

Consumer request and executed handoff: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788845224149089

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
