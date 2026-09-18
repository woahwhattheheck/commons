# Herd-purchasing packet for Sanskrit Juggernaut and Claude

Bryce's instruction on September 7, 2026:

> Give all stuff to sanskrit juggernaut so it can prompt claude for testing and running simulations

**Start with [CLAUDE_PROMPT.md](CLAUDE_PROMPT.md).** It is the purchasing-lane execution
prompt covering the source map, test requirements, simulations, selection,
reporting and existing peer ownership. [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)
records the actual source hashes and all eight generated candidate hashes.

The new purchasing work is **prepared, not simulated**. SORREL parsed its two
new Python modules and generated all eight standalone candidates; no new herd
contract tests, development games, validation games or promotion have occurred.
There is no new selected `main.py` or performance claim from this lane.

## Everything already available to consume

| Component | Location | State / owner |
|---|---|---|
| Accepted farming implementation, original incumbent, tests and economics | [20260907-offline-agent](../20260907-offline-agent/) | Euler; preserved |
| Stronger lean20 standalone, frozen study, diagnostic observer, full licenses | [cloud-market](../cloud-market/) | ASTRA-WORK; delivered and measured |
| Official-interpreter tournament driver, process isolation, timing, replay and fault tests | [cloud-eval](../cloud-eval/) | ASTRA-WORK; reusable |
| Eight new herd-purchasing hypotheses | [variants.py](variants.py) | SORREL; prepared, untested |
| Resumable development / validation driver | [experiment.py](experiment.py) | SORREL; prepared, untested |
| Harvesting / scheduling / liquidation work | Rowan's announced `cloud-dispatch/` continuation; obtain exact published ref in thread | Rowan; no unpublished bytes possessed by SORREL |
| Crop / scarcity / price work | `cloud-crop-economics/` per root's routing; obtain exact published ref in thread | Kestrel |
| Combined Claude handoff | `revenue/kaggriculture/claude-handoff/` | LARK; incorporate this purchasing packet |
| Kaggle account, public notebook and replacement submission | [Existing notebook v2](https://www.kaggle.com/code/tokenjunkielabs/tokenjunkielabs-farm-manager?scriptVersionId=347872961) | Account/root; successful submission 347872961 |

Coordination: [Kaggriculture source thread](https://tokenjunkielabs.slack.com/archives/C0BUY2GT8P9/p1788752325435209).
The owner's new routing directive was relayed there at
[1788762372.006629](https://tokenjunkielabs.slack.com/archives/C0BUY2GT8P9/p1788762372006629).
Root explicitly identified itself as Sanskrit Juggernaut at
[1788762341.574499](https://tokenjunkielabs.slack.com/archives/C0BUY2GT8P9/p1788762341574499)
and requested delivery through this same thread, with LARK aggregating the
`claude-handoff/` manifest. Root drives Claude's existing cloud VM; do not send
competing instructions into that browser session.

## Accepted evidence to carry forward

Lean20 is commit `5d9fe82d288ee2933b38e8db8871602e688410af`, standalone SHA-256
`d9487c031b50ede06a706acc8bcb40e0b5a681d9b5e92c1a1a96492b26c2dd62`.
The team's delivered results are 42 tests, 96 development games, 64 reserved
validation games, four replays and eight diagnostic-equivalence games. Validation
wins were 15/16 against each Euler28 and compact22, and 16/16 against each original36
and starter. The two losses remain documented in
[cloud-market/ECONOMICS.md](../cloud-market/ECONOMICS.md).

Use [successful post-merge run 34087144544](https://github.com/woahwhattheheck/commons/actions/runs/34087144544)
and [artifact 10005701500](https://github.com/woahwhattheheck/commons/actions/runs/34087144544/artifacts/10005701500)
for the complete prior source/results package. These are inherited team results;
SORREL did not rerun those simulations. They are not hosted rankings or prize money.

## New experiment

Lean20 forecasts placed livestock but does not count animals already bought and
waiting in its own shed or being carried. The new purchasing function optionally
adds this known pending supply. Other declared hypotheses adjust the purchase
batch, value relative to acquisition cost, expected demand from future shops,
or price impact of the planned batch. These are hypotheses, not demonstrated
improvements. The entire worker-action scheduling block is retained verbatim.

| Candidate | Change from lean20 |
|---|---|
| lean20 | Exact unchanged control |
| pipeline | Count pending livestock in the product-supply forecast |
| pipeline_single | Pipeline plus one animal per purchase order |
| capital | Pipeline plus ROI divided by relative purchase cost |
| balanced | Pipeline plus square-root capital weighting |
| future_town | Pipeline plus expected newly unlocked shop demand |
| future_capital | Future-town and square-root capital weighting |
| batch_marginal | Pipeline plus projected output of three additional animals |

Development: seeds **1543, 4787, 9431**, both seats, versus exact lean20 and
Euler28: **96 games** including the unchanged control. Select by the smaller
opponent mean margin, then overall mean, then name. The control can win.
Only selected exact bytes advance to seeds **10657, 15467, 27653, 39019, 56393,
79139, 110221, 190027**, both seats, versus lean20, Euler28, frozen compact22 and
goose20: **64 games plus four deterministic replays**. Goose20 is an ablation,
not independent strong opposition. Do not tune on reserved validation.

Root has requested strong public Kaito/Igor opponents in addition to the above.
`--opponent NAME=PATH[::FUNCTION]` adds each exact prepared public agent to
development and validation. Repeat the same set in both phases; changed or
missing opponent bytes are rejected. With both added, the counts are **192
development games and 96 validation games plus six replays**. Selection includes
all four development opponents. Root supplies their exact source/extraction
records; no public opponent code or hash is invented in this package.

## Source and licensing

Official engine pin: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
The existing evaluator checks all three upstream Git blob IDs. Preparation fetches
only public source; no competition dataset, credential or physical-device content
is included. Development and validation consume the prepared files offline.

Owner-authored code and documentation retain **MIT OR CC-BY-4.0**, with the full
texts in this directory. Attribution: Bryce Xavier Muhlnickel / TokenJunkieLabs;
Euler's original implementation; ASTRA-WORK's lean20, study and evaluator;
SORREL's purchasing continuation and handoff. Upstream Kaggle source remains
Apache-2.0 and is not relicensed.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
