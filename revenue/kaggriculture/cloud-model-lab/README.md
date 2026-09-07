# cloud-model-lab

TITAN model/benchmark lane. Scope: run measurements on this cloud VM and hand
results to the builders. This directory does not modify the accepted standalone,
`cloud-eval/`, `cloud-market/`, or any peer path.

## Environment

Cloud VM only. Nothing here is built or downloaded on Bryce's machine.

- 4 vCPU Intel Xeon @ 2.80GHz, `avx512f/bw/dq/vl/cd` + `avx512_vnni`
- 16 GB RAM, ~27 GB writable disk, **no GPU / NPU** (no `/dev/nvidia*`, no `/dev/dri`)
- Engine: PyPI `kaggle-environments` 1.32.7. Its
  `envs/kaggriculture/kaggriculture.py` and `kaggriculture.json` are
  **byte-identical** to the pinned Kaggle commit
  `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`, so the packaged install and the
  three-file fetch are interchangeable here.

## Pinned public opponents

Retrieved anonymously via `https://www.kaggle.com/api/v1/kernels/pull/{owner}/{slug}`,
notebook JSON parsed, literal base85+zlib payload decoded, `main.py` hashed.
Both current notebook versions decode to the pinned SHA-256, so no version
recovery was needed. Upstream Apache-2.0 terms are preserved; these files are
fetched for evaluation and are not republished here.

| Opponent | slug | bytes | sha256 | pin |
| --- | --- | --- | --- | --- |
| Kaito v43 | `kaitofukami/103-128-fresh-public-v43-sparse-shop-hybrid` | 63,309 | `69f06a80…3dadf3` | scriptVersion 344404785 |
| Igor | `flexonafft/kaggriculture-multi-route-farming-agent` | 148,200 | `8ac34abc…3669a0` | scriptVersion 343725556 |

## Measured results

All games are full 720-turn episodes on the official engine, both seats, all
`['DONE','DONE']` — no crashes, no timeouts. Development seeds are fresh and
disjoint from the seeds used by prior studies.

### Paired benchmark, seeds 271828/161803/141421/173205/223606/264575/302775/577215

| Matchup | Record | Mean margin |
| --- | --- | --- |
| Euler28 vs Kaito v43 | 1/16 | −40,833 |
| lean20 vs Kaito v43 | 0/16 | −41,667 |
| Euler28 vs Igor | 0/16 | −63,025 |
| lean20 vs Igor | 0/16 | −60,102 |

### Development pairs, seeds 999331 / 1299709

| Matchup | Record | Mean margin |
| --- | --- | --- |
| lean20 vs Kaito | 0/4 | −45,704 |
| lean20 vs Igor | 0/4 | −48,820 |
| **Kaito vs Igor** | **4/4** | **+12,994** |

Kaito is the stronger of the two public references on these pairs.

### Diagnostics (seed 999331)

| | lean20 | Kaito | Igor |
| --- | --- | --- | --- |
| gross (repriced requested orders) | 56,212 | 172,347 | 174,739 |
| wheat feed spend | **17,672** | **0** | **0** |
| hire orders | 194 | 282 | 277 |
| land bought | 0 | 2 | 2 |
| cold start | 0.2 ms | 0.4 ms | 0.2 ms |
| decision p50 / max | 0.57 / **106.8 ms** | 0.37 / 2.4 ms | 0.28 / 1.9 ms |
| unsold shed at end | `{}` | `{}` | `{}` |

`gross` reprices *requested* market orders against the inventory observed on
that turn. Requested orders are not assumed to execute; the score rows are the
ground truth. Terminal liquidation is clean for all three agents.

### Realized revenue attribution (for KESTREL / SORREL)

Seeds 271828 and 141421, lean20 vs Kaito:

| Product | lean20 | Kaito |
| --- | --- | --- |
| STRAWBERRY | 0 / 0 | 432 units / +75,816 and +84,839 |
| WHEAT | −395 / −17,098 and −467 / −20,862 | +221 / +13,255 and +13,094 |
| MILK | 485 / 25,799 | 335 / 24,116 |
| WOOL | 154 / 26,161 | 179 / 29,267 |

Two observed structural gaps, both confirmed independently at the source level
by root (`lean20` `CROPS` contains only WHEAT/CARROT/MELON — no STRAWBERRY or
TOMATO):

1. **Strawberry.** Four of the eight shops demand it (`BRUNCH_SPOT`,
   `ICE_CREAM_SHOP`, `SMOOTHIE_SHOP`, `FARMERS_MARKET`), so town drain holds it
   scarce; it ended at −47 inventory / $178 against a $120 base rather than
   glutting.
2. **Wheat feed.** ~18k/season spent buying feed that neither opponent buys.

Igor reaches a comparable gross by a different route (`FERTILIZER` 2,932 units
requested / 73,938), so this is not a single exploit.

Market state at end of a representative season (relative to `I0` = 10000):
`WHEAT -762 ($53)`, `TOMATO -282 ($126)`, `CARROT -205 ($51)`, `EGG -117 ($57)`,
`MILK +74 ($5)`, `FERTILIZER +493 ($1)`, `MELON +65 ($208)`, `WOOL +7 ($197)`.

## `market_layer.py` — kept as a model, wrapper not promoted

`market_layer.py` reimplements the official price curve and town-drain schedule
from the engine's public constants. Its `market_price` is verified **exactly
equal** to `kaggriculture.market_price` across every product over inventories
9000–12000, so it is reusable as a pricing/demand oracle.

`hybrid.py` wraps an unmodified base policy with it, filling only the market
order slots the base policy left unused. **It did not earn promotion.** Same
opponents, same seeds, against unchanged lean20:

| Opponent | lean20 | hybrid | Δ |
| --- | --- | --- | --- |
| Kaito | −45,704 | −46,070 | −366 |
| Igor | −48,820 | −51,074 | −2,254 |

The one-tick round trip is worth only 5–32 coins, which does not cover the shed
space and working capital it consumes. Hypothesis closed. One side effect is
worth recording: on seed 999331 the layer suppressed Kaito to 71,238 from his
usual ~87,000 by competing for market inventory, while costing us more than it
gained on 1299709 — a denial effect, not a revenue one.

## Gemma 4 E4B on this VM

Artifact and runtime independently agreed by root against LDA
`kite-help@54081cd5` `docs/E4B_ARCHITECTURE.md:49-51`.

- artifact: `gemma-4-E4B-it.litertlm`, 3,659,530,240 bytes,
  sha256 `0b2a8980ce155fd97673d8e820b4d29d9c7d99b8fa6806f425d969b145bd52e0`
- source: `litert-community/gemma-4-E4B-it-litert-lm` (Apache-2.0, ungated)
- runtime: PyPI `litert-lm==0.16.1`, the LDA-pinned version. No llama.cpp.
- backend: CPU (no accelerator on this VM)

`google/gemma-3n-E4B-it-litert-lm` is `gated: manual` and Kaggle's model
download returns 403 without credentials; neither was needed and no 3n
checkpoint was substituted.

### Measured, real inference

One real Kaggriculture observation, CPU backend, LiteRT-LM 0.16.1:

| metric | value |
| --- | --- |
| RSS at import | 78 MB |
| RSS post-load | 612 MB |
| **peak RSS** | **4,356 MB** |
| **cold load (page cache empty)** | **21.22 s** |
| warm reload (page cache hot) | 0.58 s |
| **decision latency** | **10.72 s** |
| model output | `SELL STRAWBERRY 12` |

The output is a legal action and the correct one for that observation
(12 strawberry held, $178/unit, three shops demanding strawberry).

Consequences for the entry, measured rather than assumed:

- 10.72 s/decision against Kaggle's 1 s `actTimeout` plus a non-replenishing
  60 s overage bank means E4B **cannot sit in the per-turn decision path**.
  Even one call per in-game day (30 calls) is ~321 s, over 5x the whole bank.
- Peak RSS 4,356 MB fits the 6.5 GiB runtime limit, but the 3.66 GB artifact
  cannot fit the 100 MiB submission cap. The cloud lane and the final offline
  entry remain separate constraints.
- `Conversation.token_count` returned `None` under 0.16.1; prompt/output token
  counts are still outstanding.

Reproduce: `python e4b_test.py` (see `scratchpad`; model path is a constant).

## Files

- `market_layer.py` — official price curve + town drain, verified exact.
- `hybrid.py` — additive wrapper; measured, not promoted.
- `README.md` — this file.
