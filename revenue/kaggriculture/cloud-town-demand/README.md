# Public-town schedules and dated-flow integration

`town_demand.py` supplies town-only inventory schedules from public state and explicitly declared shop draws. `flow_scenarios.py` passes those draw identities to the existing ROUTE-FLOW consumer at the correct first-active action. FLOW keeps pricing, paired rival receipts and town consumption; DATE keeps route ranking. No controller, simulator, probability model or second inventory update is introduced.

## Call the existing flow consumer

```python
from flow_scenarios import make_flow_scenario

scenario, town_report = make_flow_scenario(
    observation, configuration, official_mechanics, flow.Scenario,
    name="declared_five_draws",
    future_shops=("YARN_STORE", "BAKERY", "BAKERY", "BAKERY", "BAKERY"),
    rival_orders={},
)
report = flow.evaluate_scenarios(offers, observation, configuration,
                                 market_mechanics, [scenario])
if report["complete"]:
    selector = date.DatedSelector(flow.as_cash_scenarios(report, date.CashScenario))
    chosen_route = selector(offers, observation)
```

Supply the draw count appropriate to the current observation, not always five. `official_mechanics` is the caller's already-loaded pinned interpreter with `MAX_SHOP_INSTANCES`; the frozen quotation mechanics module omits that constant. No engine is downloaded or initialized by the runtime.

An unlock after action287 first appears in observation288. Trades at288 still occur before that turn's town consumption. The adapter therefore emits `shop_additions={288: (...)}`, never applies inventory deltas itself, and retains duplicate names and the eight-instance cap. A draw after the final playable market is recorded but not passed as another playable turn. Missing future draws are not silently represented as a complete scenario. `None` is accepted only when no unlock remains.

Each supplied path is a conditional scenario, not an exhaustive scenario bank or a probability distribution. `scenario_family` groups only selected-product consumption signatures; it does not make different public shop identities interchangeable for an adaptive controller. When valuing complete multi-product routes, preserve the actual shop identities or include every affected product. Do not add `DemandSchedule` deltas to FLOW: FLOW already performs that consumption.

## Reproduction

Reuse engine artifact10005621438 and the existing source closure. The engine directory includes `kaggriculture.py` and its sibling `kaggriculture.json`. The interpreter SHA-256 is `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`; the test loader omits only the unavailable framework seed-helper import and refuses initializer use.

```sh
python -B test_flow_scenarios.py --engine "$ENGINE/kaggriculture.py" \
  --flow ../cloud-capital-route-flow/dated_flow.py --report /tmp/town-flow-tests.json
```

For current reader adoption, optional budget arguments and incomplete-result exit codes, see [JOINED-CLI.md](JOINED-CLI.md). Use an exact dependency closure; moving main may contain different peer revisions.

For the natural-input join, reuse Library `osprey-reached-quote-case.zip`, file `file_00000000d93881f5949750cf2733e3ad`. Its unchanged `evidence/saved-226-row.json` is TRACE's DELVE control input, not HAZEL's missing candidate checkpoint. The source closure uses the PR10216 FLOW and reader revisions plus the other source pins already declared by OSPREY's reader.

```sh
python -B joined_case.py --input "$PACKAGE/evidence/saved-226-row.json" \
  --paths declared-paths.json --source-root "$PINNED_SOURCE_ROOT" --engine "$ENGINE/kaggriculture.py" \
  --output /tmp/town-flow-joined.json
```

The CLI reuses OSPREY's `compare_saved_input`, not a second quote/ranking implementation. It makes no agent action or full-game call. The nine paths specify all remaining draws: each possible first shop followed by four BAKERY draws, plus five YARN draws. They are declared sensitivity cases, not exhaustive support. Rival orders are explicitly empty. Future shops never become features of the saved226 observation.

## Executed scope

The original runtime and full original test source are preserved byte-for-byte from the earlier Library package. That retained run contains18 methods,47 controlled cases and16,210 interpreter transitions. It was not rerun as new evidence.

The new integration passes12 methods and34 interpreter transitions across eight controlled arrival/trade cases, both player positions. The saved-input join reconciles18 route/scenario records and3,915 variable cash rows. The declared bank retains MAIN; nominal SHEEP-minus-MAIN ranges from -7,235 to +10,720. This is scheduled-volume valuation, not physical fill evidence, game strength or policy promotion.

A fresh main read found PR10216's completion-deadline repair. The new integration deliberately consumes FLOW `ddbbe439c93082ab68b2e7e8dcfe302bbee052e7` and OSPREY reader `794b56813daf89e06b76aaa8cbb291498e15c73c`. The full joined output is identical to the earlier-source run except explicit source provenance and measured elapsed time. Existing deadline checks stay intact; no peer source is edited here. Tests also accept the original exact pins for reproduction of historical results.

`RESULTS.json` retains source identities, measured scope and compact conditional results. Complete reports, old-source results, original source/engine evidence and setup logs stay in the AMBER Library delivery. One measured quote/flow/ranking execution is not a whole-agent latency guarantee. Neither the selected candidate nor any frozen game panel changes.

Existing consumer thread: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805915221339
