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
python3 -B -m unittest -v
Ran 13 tests in 1.327s — OK

syntax compile of capacity_ledger.py, test_capacity_ledger.py,
run_witnesses.py — OK

two independent run_witnesses.py outputs — byte-identical
workflow YAML local parse — OK
```

The tests include 5,184 exhaustively enumerated post-market-room states and 880
same-unit-stage retained-PLACE ordering states: 6,064 enumerated states total.
The machine receipt is `RESULTS.json`; `run_witnesses.py` emits the five
positive/counterexample traces deterministically.
A dedicated NEW `.github/workflows/titan-w08-capacity-throughput.yml`
replays the same proof on pull requests and retains logs, witness JSON, and
hashes. Its remote result is intentionally reported in the PR/Slack receipt,
not pre-claimed here.

## Authored file identities before Git publication

| File | SHA-256 |
|---|---|
| `capacity_ledger.py` | `2b698df6e0cf61e604a8446af78f7ed6bebad49eb6a0cd4584014496df84745f` |
| `test_capacity_ledger.py` | `9d87b26d022b88f8c9f93569e1cce59be7e6f37aef603f22febb6e9aa8a38b22` |
| `run_witnesses.py` | `8adc05e70ec9b5cc5909ada048e1133108579908e02868636fb3b4a11fa480d9` |
| `README.md` | `85db4808a6ff6c391782151e59acf8adaeda7622aacc768a2b5070f9ce3e2f87` |
| `.github/workflows/titan-w08-capacity-throughput.yml` | `a962b1aa366061437cb62c02b7d357b3b98f034a2f5f6268b122ebaea1f81136` |
| `RESULTS.json` | `cbff12da530d3762a62e273c1a0df59e486bb1862e94f8a715c035f87da8f477` |

## Boundary and next integration

This publication intentionally does **not** mutate the canonical TITAN runtime,
archive, selected producer, E20 source, game harness, provider, or Kaggle
submission. It is a tested source primitive and exact integration recipe for the
current producer/F1 owner. A canonical consumer should translate only its known
selected tape, bind market quantities to executable fills, and require additive
admission before reporting a completed harvest/deposit job. Full matched games
remain required before any playing-strength claim or default expansion.
