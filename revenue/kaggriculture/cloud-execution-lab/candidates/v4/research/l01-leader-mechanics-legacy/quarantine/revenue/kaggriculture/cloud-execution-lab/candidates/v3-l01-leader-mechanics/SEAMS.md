# L01 seams in canonical 3b4b (MAIN tape 7015cc00acfa4922)

from: TITAN (this is a claim, not a seat)
Archive SHA256: 3b4b083ec2647bb0e715978c2565e916da0ee94c08b234902e3a7e4d3418c320
Commit pin: ba1efc8732073d7ad566ea5090fb9aa3e8b2bc33
main.py SHA256: 0dae922de836cdb590891d9bbca9a58e18114ebcc64e16fb5b264311f07133e5
TITAN-CONFIG.json has no land / animal / plant / day-0 / tranche keys.
Those decisions live in Arlene MAIN, not TITAN-CONFIG.
Flags cannot be os.environ: evaluate.py Actor env is {PATH,HOME,LANG,PYTHONHASHSEED,PYTHONDONTWRITEBYTECODE}.

| mechanism | file:function:line | current constant | L01 mutation |
|---|---|---|---|
| BUY_LAND timing | arlene.py:Agent.act:511-515 reads route[step]['market']; tape posts at t=150 and t=265 | LAND_ORDER mechanics.py:84 `["NE","SW","SE"]`; LAND_PRICES mechanics.py:87 `[1000,2000,4000]`; engine `_do_buy_land` kaggriculture.py:712 no-ops after 3 unlocks or if cash < price | TITAN_L01_LAND appends `["BUY_LAND"]` at t=74 and t=98 (slot room: 1 and 1). Keep 150/265 fallback. |
| animal mix | same tape BUY_ANIMAL; scheduler.py:_order_spend:187 `m.ANIMALS[item]['cost']*n`; ANIMALS mechanics.py:17-21 COW 400 / SHEEP 500 / GOOSE 300 | TITAN live COW 9 + SHEEP 5 + GOOSE 3. Opening t=1 keeps COW 2 + SHEEP 2. Later COW at 65,88,150,169,176,195 | TITAN_L01_SHEEP rewrites BUY_ANIMAL COW after t=1 to SHEEP (6 orders / 7 head). Result COW 2 + SHEEP 12 + GOOSE 3. |
| day-0 product buys | tape t=0 market `[["BUY_PRODUCT","WHEAT",13]]`; engine BUY_PRODUCT only WHEAT/FERTILIZER (kaggriculture.py:598) | SpaTaro posted CARROT 14 MELON 20 MILK 40 STRAWBERRY 8 TOMATO 12 WHEAT 2 (fills not in replay; basket list price 13620 vs cash 3000) | TITAN_L01_DAY0BUY replaces t=0 market with that basket. Non-WHEAT/FERTILIZER BUY_PRODUCT abort in 1.32.7. |
| sale tranches | scheduler.py:SellScheduler.act:292-386; frozen_selected.py:materialize_sales:14-29; selected_sell_core.py:optimize_lot share in (1,2,3) remaining*share//4 at selected_sell_core.py:113-135 (scheduler twin); arlene.py:_terminal_settlement:345; FINAL_EXECUTABLE_STEP=718 | Day-29 tape: t=697 WHEAT 50 + CARROT 7; TITAN fertilizer drip. Otter posted WHEAT 57 + CARROT 32 plus multi-product lots | TITAN_L01_TRANCHE live after act, day>=28, step<718: ensure SELL WHEAT min(shed,57) and CARROT min(shed,32); pack other shed products except FERTILIZER. Terminal 718 left to _terminal_settlement. |
| lean planting | tape PLANT units; spatial_tempo.py:unit/set_unit:16-24 | SpaTaro 148 plants / Otter 177 / TITAN 240 = MELON 12 WHEAT 164 STRAWBERRY 33 CARROT 31 | TITAN_L01_LEANPLANT converts last 92 PLANT WHEAT to PASS (WHEAT 72, total 148). |

Flag off: patch_routes is a no-op and records reason `L01_noop:flag_off`. apply_tranche returns the same action object.
