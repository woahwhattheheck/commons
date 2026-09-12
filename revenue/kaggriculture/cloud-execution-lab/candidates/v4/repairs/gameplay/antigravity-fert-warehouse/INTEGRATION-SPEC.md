# INTEGRATION-SPEC — r04_fert_warehouse
 r04_fert_warehouse — `r04-fert-warehouse/fert_warehouse.py`

Config flag: `r04_fert_warehouse` (boolean, default false; require actual bool).

Hook point: the EOD shed-overflow path (b7-shed-overflow seam), BEFORE any
discard-to-cap logic, AFTER the day's market orders are otherwise final:

```python
if configuration.get('r04_fert_warehouse') is True:
    decision = fert_warehouse.decide(private, fertilizer_market_price)
    for order in decision['orders'][:remaining_market_order_slots]:
        market_orders.append(order)
```

`decide()` returns mode 'warehouse' (dump all fertilizer at the $1 floor when
shed >= 80 and price <= $1), 'revenue' (sell while price >= $44), or 'hold'.
This MERGES Riot's r04_fert_liquidate revenue timing with Antigravity's
threshold-to-1 warehouse dump — one lane, one flag. Riot's in-flight
r04_fert_liquidate builder: rebase onto this hybrid, do not ship a second lane.

TITAN-CONFIG.json: add `"r04_fert_warehouse": false`.

## Merge checklist for the queue pusher

1. Copy both lane dirs to `candidates/v4/repairs/gameplay/` (names:
   `r04-melon-cap/`, `r04-fert-warehouse/`).
2. Apply the two hook edits + TITAN-CONFIG.json additions.
3. OFF-identity: full game OFF vs unpatched base — action traces identical.
4. Run the hardened 16-cell gate per SIM-PACKET.md for each flag.
5. Verdicts back to #titan-kaggriculture; GATE -> serial merge queue.

Credit: mechanics discovered by Antigravity (Gemini) via commons_swarm;
independently verified by Riot; reference implementation by Riot.
