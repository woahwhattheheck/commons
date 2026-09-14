# DARPA DV026 market POC

This directory is an **internal pre-proposal technical spike** for Commons issue
[#13534](https://github.com/woahwhattheheck/commons/issues/13534), DARPA topic
`DPA26BZ06-DV026` ("Influence Benchmarks for AI Systems").

It is deliberately smaller than a Phase-I system. It proves that Commons can
represent and test the missing economic-evaluation seam without pretending that
proposal eligibility, a ten-LLM experiment, human calibration, award, or revenue
already exists.

## What is implemented

The spike is dependency-free and offline:

- strict scenario, participant, news, order, and adapter contracts;
- deterministic public-news shocks that change participant reservation values;
- a black-box adapter boundary: an adapter receives only its observation and
  returns one strict order; the harness does not inspect model internals;
- two market mechanisms over the same book:
  `CONTINUOUS_DOUBLE_AUCTION` and `UNIFORM_PRICE_CALL`;
- deterministic tie-breaking and bounded unit expansion;
- realized social surplus versus the scenario's optimal feasible surplus;
- allocative efficiency in basis points with a configurable gate (default
  `9000`, i.e. 90%);
- canonical SHA-256 binding of scenario, public news, orders, trades, and the
  receipt;
- a model-panel receipt that distinguishes `SYNTHETIC_STUB` from
  `EXTERNAL_BLACK_BOX`;
- explicit non-authority flags for contact, submission, provider calls,
  registration/signature, spend, award and revenue;
- hostile regressions for strategic misallocation, strict input custody,
  adapter identity, deterministic ties, receipt tamper, news ordering, and
  synthetic-vs-external model truth.

The engine exposes the economic metric instead of optimizing it away. A
strategic order profile can therefore clear trades and still fail the
allocative-efficiency gate.

## The ten-model boundary is intentionally fail-closed

A scenario can name any number of synthetic model IDs for offline testing.
Those IDs **do not** satisfy the external-model contract. The receipt separately
reports:

- all distinct model IDs;
- distinct IDs whose adapter kind is `EXTERNAL_BLACK_BOX`;
- whether at least ten distinct external-black-box IDs are represented;
- `ten_llm_milestone_claimed: false` unconditionally.

Even a test fixture containing ten synthetic stubs therefore cannot be
misreported as the DARPA Month-9 ten-LLM milestone. Connecting real models is a
future, separately authorized experiment that must bind actual provider/model
identity and usage evidence.

## Public news

Each news event is totally ordered by a contiguous `seq` and contains a public
headline plus deterministic buyer-value and seller-cost deltas. Every agent
observation receives the same ordered public-news transcript. The evaluator
applies those deltas to the private reservation values before computing both
realized and optimal surplus, so the efficiency metric is evaluated against the
same information state the agents saw.

This is intentionally a minimal dynamic-information plane, not a news
classifier or a claim that DARPA's full Phase-I information environment has
been completed.

## Market mechanisms

Both mechanisms rank bids high-to-low and asks low-to-high and trade only while
`bid >= ask`.

`CONTINUOUS_DOUBLE_AUCTION` prices each deterministic matched unit at the
integer midpoint of its bid and ask.

`UNIFORM_PRICE_CALL` computes the same feasible crossing allocation but prices
all matched units at the midpoint of the marginal crossing bid/ask.

The shared allocation is useful for separating **allocation quality** from
mechanism-specific transfer prices in early experiments. More market designs
can be added without changing the receipt contract.

## Efficiency

For each traded unit:

```text
realized surplus = buyer news-adjusted reservation - seller news-adjusted cost
```

The optimal benchmark sorts all buyer reservation units high-to-low and all
seller cost units low-to-high, then takes every positive-surplus pair.

```text
allocative_efficiency_bps = floor(realized_surplus * 10000 / optimal_surplus)
```

The default POC gate passes at `>= 9000` basis points. A zero-opportunity market
has 100% efficiency only when realized surplus is also zero.

This metric is an internal engineering discriminator. Passing it on a fixture
is **not** evidence that the official DARPA >90% milestone has been met.

## Reproduce

From the repository root:

```bash
python -m unittest -v research.darpa_dv026_market_poc.tests.test_engine
python -O -m unittest -v research.darpa_dv026_market_poc.tests.test_engine
python -m py_compile \
  research/darpa_dv026_market_poc/engine.py \
  research/darpa_dv026_market_poc/cli.py \
  research/darpa_dv026_market_poc/tests/test_engine.py

python -m research.darpa_dv026_market_poc.cli evaluate \
  research/darpa_dv026_market_poc/fixtures/synthetic_panel.json \
  research/darpa_dv026_market_poc/fixtures/synthetic_truthful_orders.json \
  --mechanism CONTINUOUS_DOUBLE_AUCTION
```

The bundled fixture intentionally uses ten `SYNTHETIC_STUB` model IDs. It should
produce a high-efficiency economic receipt while still reporting
`external_black_box_model_count: 0` and
`ten_distinct_external_model_contract_met: false`.

## What remains before a Phase-I bid can call the technical risk closed

1. Bind the controlling solicitation and owner/entity eligibility facts called
   out in #13534.
2. Implement separately authorized adapters for **actual** distinct LLMs and
   bind provider/model/version evidence without leaking credentials.
3. Add a larger family of market/auction designs, scenario distributions and
   adversarial information shocks.
4. Ingest an allowed published or previously acquired human-market reference
   dataset and define calibration/comparison metrics.
5. Build the Phase-I behavioral-preference/classifier framework required by the
   topic; do not over-import later deception metrics into the Phase-I claim.
6. Run repeated heterogeneous-model panels with cost, latency, failure,
   reproducibility and provenance receipts.
7. Demonstrate the official >90% allocative-efficiency criterion on the
   controlling evaluation design, not merely on these engineering fixtures.
8. Package Government-runnable software/data delivery only after solicitation,
   licensing, compliance and owner authorization are resolved.

## Authority ceiling

This code performs no network call, model-provider call, sponsor contact,
proposal submission, registration, signature, spend, payment, award or revenue
recognition. It does not establish SBIR eligibility and does not mutate any
external service.

Primary opportunity and FAQ links remain tracked in #13534. This carrier
changes engineering evidence only.
