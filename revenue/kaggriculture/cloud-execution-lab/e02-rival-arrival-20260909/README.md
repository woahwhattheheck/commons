# E02 first-screen evidence — rejected candidate

Operation: `titan-v25-orders-20260909-E02`

Status: **DO NOT MERGE UNGATED**. PR #11119 is closed unmerged. No Kaggle/provider submission occurred.

Official-engine first screen: 32 seed/opponent pairs x both seats = 64 complete games per variant, engine ref `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.

- Starter control: 32/32 seat games exact inherited trace/cash; base 32W/0L, E02 32W/0L.
- Arlene: 32/32 seat games activated; base 32W/0L -> E02 28W/4L. Mean candidate cash delta +780, but mean relative-margin delta -152.6875. Seed-cluster bootstrap 95% interval [-753.71875, +466.1875], 7 positive / 9 negative clusters, worst seat delta -2353.
- Example W->L cluster seed 614776397: inherited +1096 margin -> E02 -638 (-1734/seat). First seller delta step269 MILK 6->5 on a certain public q6 harvest hypothesis with arrival 269..288; candidate unit actions did not change in the compact loss delta trace.
- Three multi-seed driver invocations were externally cut by the session wrapper after partial complete-game lines; they are excluded from the atomic 64-game/variant screen. This is not counted as an agent/game timeout.

Files:

- `FIRST-SCREEN-SUMMARY.json` — plain JSON. Raw SHA256 `f7e1f1b6bcff384096a12bb1d6eec62d184ac5a68e043a65334f7929667d5d43`.
- `FIRST-SCREEN-GAMES.csv.gz.b64` — base64 of deterministic gzip (`mtime=0`) containing the exact 64 matched seat-pair CSV rows per variant. Decode with `base64 -d ... | gzip -dc`. Raw decoded CSV SHA256 `f92ce5f1f861c0449585b8e35a02a6e3dbf507a029a2dd59f7c13560a7c91d2f`; gzip SHA256 `74534be34f303d055fca0130a5b5cdd0761e751ac888dd050adc6bf9c424512b`.
- `FIRST-SCREEN-CLUSTERS.json.gz.b64` — base64 deterministic gzip of seed-cluster rows. Raw JSON SHA256 `80b247e24be8133c2c174e8ca03fd204060ce067c4f31631923a6468fc9fd190`; gzip SHA256 `5d53e4ed89ff3e93eed72e2dcddd04202e1a091daceb28573ab5fe9434a63c7e`.
- `LOSS-614776397-MARKET-TRACE.csv.gz.b64` — base64 deterministic gzip of compact market-only base/E02 delta rows for both seats. Raw CSV SHA256 `831c10df66bbcd95bd23d5674d7e896a49fc2938918fec28b6b443be24c30bb9`; gzip SHA256 `68dcad092bf0a1b2b539d1f23c2a69cb50c89225c37c4b4aef136253a52012f6`.

The corresponding E02 source remains on this rejected branch for diagnosis only. Focused exact-package regression suite was 9/9 PASS; the bounded official-game evidence above rejected canonical integration because reactive-opponent relative cash and W/L regressed despite positive mean own-cash movement.
