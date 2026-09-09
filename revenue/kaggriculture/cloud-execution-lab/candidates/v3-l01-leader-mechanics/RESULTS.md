# L01 leader-mechanism candidates on canonical 3b4b

from: TITAN (this is a claim, not a seat)
carrier: Grok Build background / TITAN
id: titan-l01-leader-mechanics-20260909

S11 was not duplicated (canonical S11 is PR #11239). live `exports/titan-current.tar.gz` SHA256 `a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba` left for Bryce.

Canonical archive: `exports/historical/titan-3b4b083ec2647bb0e715978c2565e916da0ee94c08b234902e3a7e4d3418c320.tar.gz`
SHA256: `3b4b083ec2647bb0e715978c2565e916da0ee94c08b234902e3a7e4d3418c320`
Commit pin: `ba1efc8732073d7ad566ea5090fb9aa3e8b2bc33`
Extract main.py SHA256: `0dae922de836cdb590891d9bbca9a58e18114ebcc64e16fb5b264311f07133e5` (byte-identical kept as `overlay/canonical_main.py`)
Engine: kaggle-environments==1.32.7 commit `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`
Engine sha256: kaggriculture.py `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e` json `a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867` utils `537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b`
Runner: copy only `gauntlet_l01.py` (POOL already listed the six opponents). Original `tools/v25_sims/gauntlet.py` not edited. evaluate.py not edited.

TITAN-CONFIG.json keys (frozen, no production-timing knobs): consumer, seed, funding, terminal_route, committed, budget_seconds, reserve_seconds, terminal_history, redundant_hire, fourth_quadrant, market_pressure, committed_seed_retry, operating_stock, idle_fertilizer, crop_release. Land / animals / day-0 buys / plants / tranche sizing live in Arlene MAIN `7015cc00acfa4922`. evaluate.py strips worker env, so flags are baked in `l01_flags.py`.

See SEAMS.md for file:function:line.

## Commands

```
# pytest (from an overlaid 3b4b extract)
python -m pytest -q test_l01_mechanisms.py
# 9 passed

# panel (one candidate)
V25_REPO=/tmp/commons V25_WORK=/tmp/v25 python -B gauntlet_l01.py \
  --seeds 2611061001,2611061002,2611061003,2611061004,2611061005,2611061006,2611061007,2611061008,2611061009,2611061010,2611061011,2611061012,2611061013,2611061014,2611061015,2611061016 \
  --opponents arlene,apex,kaito_v43,cok_v10,public_bt12,v1_submitted \
  --workers 8 --action-timeout 15.0 \
  --candidate <extract>/main.py \
  --outdir <out>
```

Seeds 2611061001-016 x 6 opponents x 2 seats = 192 games per candidate. Canonical uses unmodified 3b4b main.py. Five flag candidates use overlay/main.py + one baked flag.

Holdout seeds 2611062001-016 after combining non-negative paired own-cash mechanisms.

## Tests

pytest 9 passed: flag-off identity (reason L01_noop:flag_off), LAND BUY_LAND at 74 and 98 with 150/265 kept, SHEEP converts post-t1 COW (opening COW 2 kept), DAY0BUY replaces wheat-13 with SpaTaro basket, LEANPLANT 164->72 wheat / 240->148 plants, TRANCHE enlarges WHEAT 57 CARROT 32 and packs extras, TRANCHE off is object-identity, TRANCHE skips step 718.

## Panels

## Canonical panel (unmodified 3b4b main.py)

command: `--candidate /tmp/v25/cand_3b4b/main.py --outdir /tmp/v25/out_l01/canonical --workers 8 --action-timeout 15.0 --opponents arlene,apex,kaito_v43,cok_v10,public_bt12,v1_submitted --seeds 2611061001-016`

wall_seconds 607.7  workers 8  scheduled 192  completed 192  failed 0  throughput 18.96 games/min
SUMMARY sha256 see panels/canonical.SUMMARY.json
per_opponent:
- arlene: games 32 W 24 T 0 L 8 mean_margin -2418.219
- apex: games 32 W 32 T 0 L 0 mean_margin 8943.281
- kaito_v43: games 32 W 30 T 0 L 2 mean_margin 14596.781
- cok_v10: games 32 W 32 T 0 L 0 mean_margin 26303.062
- public_bt12: games 32 W 32 T 0 L 0 mean_margin 22454.656
- v1_submitted: games 32 W 32 T 0 L 0 mean_margin 874.562

Tokens: panels/canonical.TOKENS.txt (seed:own_s0/rival_s0/own_s1/rival_s1).

## land panel

wall_seconds 549.1  workers 8  scheduled 192  completed 192  failed 0  throughput 20.98
- arlene: games 32 W 32 T 0 L 0 mean_margin 1631.031
- apex: games 32 W 32 T 0 L 0 mean_margin 8943.281
- kaito_v43: games 32 W 30 T 0 L 2 mean_margin 14596.781
- cok_v10: games 32 W 32 T 0 L 0 mean_margin 26303.062
- public_bt12: games 32 W 32 T 0 L 0 mean_margin 22454.656
- v1_submitted: games 32 W 32 T 0 L 0 mean_margin 874.562

