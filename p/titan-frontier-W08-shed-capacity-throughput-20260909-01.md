# TITAN W08 shed-capacity throughput — source receipt

**Operation:** `titan-frontier-W08-shed-capacity-throughput-20260909-01`  
**Owner:** `SOL-KESTREL-89`  
**Slack claim:** `C0C1DLNJG5N / 1788977337.569569`  
**Publication branch:** `sol-kestrel-89/titan-w08-capacity-ledger-20260909-01`  
**Fresh publication base:** `b5b19ce971339fe10eef6992059bad5091cd49a0`

## Source finding

The engine's physical order is unit actions, then market rows, then the
end-of-day inventory drop. `DROP` and the EOD drop destroy overflow, while
shed-adjacent `PLACE` retains an unplaced remainder. Market sales can create
capacity after the current unit stage, and a later product/animal buy can consume
that room again.

The existing E20 useful-hire screen correctly rejects its reported retained
PLACE-versus-new-DROP collision, but its aggregate stock test and blanket
pre-deposit PLACE/DROP veto cannot distinguish this separate W08 family:

1. shed starts with `WHEAT99`; a retained actor carries `WHEAT1`;
2. retained `PLACE WHEAT1` fills the shed to 100;
3. retained, executable `SELL WHEAT1` creates one slot in the market phase;
4. a later worker's already-harvested `WHEAT1` drops into that slot.

Every retained event completes exactly as before and no stock is discarded. The
same candidate must decline when the sale is absent, when an intervening
`BUY_PRODUCT` refills the slot, or when an earlier candidate deposit would reduce
a retained PLACE. Aggregate pre-market stock alone cannot prove these cases.

## Delivered implementation

`revenue/kaggriculture/cloud-w08-capacity-throughput/capacity_ledger.py` is a
small, policy-independent physical inventory oracle. It:

* sorts deterministic events by step, engine phase, explicit sequence, and
  stable input order;
* models HARVEST, PICKUP, PLACE, DROP, SELL, BUY_PRODUCT, BUY_ANIMAL, CONSUME,
  EOD_DROP, and PASS;
* reports requested, realized, and discarded units for every event;
* enforces shed capacity and per-item conservation; and
* admits an additive job only when every retained event keeps identical realized
  and discarded quantities, every required new event completes, and discard
  never increases.

The caller must still prove route reachability, action legality, stock/yield,
affordability, exact market ordering, and any claimed sale fill. The ledger does
not call a policy, alter a route, infer opponent-private state, invent sales,
quote future cash, or claim a game result.

## Verification actually run

```text
W08_ALLOW_ENGINE_STUB=1 python3 -B -m unittest -v
Ran 20 tests in 1.469s — OK (19 pass, 1 hosted-only engine-blob pin skipped)

syntax compile of capacity_ledger.py, test_capacity_ledger.py,
test_engine_parity.py, run_witnesses.py — OK

two independent run_witnesses.py outputs — byte-identical
workflow YAML local parse — OK
```

The model tests include 5,184 exhaustively enumerated post-market-room states
and 880 same-unit-stage retained-PLACE ordering states. The differential suite
adds 2,211 DROP/PLACE/PICKUP/market/EOD/intervening-sale comparisons against the
pinned official-engine primitives: 8,275 deterministic transitions total. The
local workspace used a byte-visible primitive stub and intentionally skipped only
the full-engine Git-blob assertion; hosted CI imports the checked-in interpreter
and must pass exact blob `3c202c7ee921da239356789e266b694635103fc4`.
The machine receipt is `RESULTS.json`; `run_witnesses.py` emits the five
positive/counterexample traces deterministically.
A dedicated NEW `.github/workflows/titan-w08-capacity-throughput.yml`
checks out and asserts the exact triggering head, replays the same proof on pull
requests, and retains logs, witness JSON, and hashes. Its remote result is
intentionally reported in the PR/Slack receipt, not pre-claimed here.

## Authored file identities before Git publication

| File | SHA-256 |
|---|---|
| `capacity_ledger.py` | `98d5c014cd4744249b9190d9a9bf5b990a6a59951860dbcb0abd5049035637d1` |
| `test_capacity_ledger.py` | `7ab7dd95c2c2289a02f2b0a4c7448cab49e7459c901715cfb341730f56fbeb03` |
| `test_engine_parity.py` | `ba082b93ecacbad5156b09239adff233d904856cf5f54c771224149b130364cb` |
| `run_witnesses.py` | `8adc05e70ec9b5cc5909ada048e1133108579908e02868636fb3b4a11fa480d9` |
| `README.md` | `3987e9fa382663bb5f694acc5a63c6fa1335251d3ad6485f83cf9e3277fbe3ea` |
| `.github/workflows/titan-w08-capacity-throughput.yml` | `d9617f572375a753bab30f2e13557300477fc3981091038e02a33d83b3f0b13d` |
| `RESULTS.json` | `0f6d304f2f4b4335b6ba334113e29b50373bf53a36305191ee59a62dae8673c0` |

## Boundary and next integration

This publication intentionally does **not** mutate the canonical TITAN runtime,
archive, selected producer, E20 source, game harness, provider, or Kaggle
submission. It is a tested source primitive and exact integration recipe for the
current producer/F1 owner. A canonical consumer should translate only its known
selected tape, bind market quantities to executable fills, and require additive
admission before reporting a completed harvest/deposit job. Full matched games
remain required before any playing-strength claim or default expansion.
