# TITAN V3 — weed-continuation factor and capital firewall

This packet isolates the hidden always-on weed-continuation factor in exact submitted V2 and introduces a bounded successor that preserves its two exact Apex wins while recovering TITAN cash.

## Exact spent-bank result

The immutable official-interpreter bank is 4 opponents × 8 already-published seeds × both seats = 64 paired cells.

- **Weed ON vs weed OFF:** active in 2/64 cells, both Apex. ON changes both losses to wins, but costs TITAN an average **$36,307** in the active cells while reducing the rival by **$41,853.50**.
- **Capital firewall vs weed ON:** active in the same 2/64 cells, byte-identical in the other 62. It preserves **64W/0T/0L**, improves TITAN by **$1,403.50 average active-cell cash**, and reduces winning margins by **$1,206.50 average**.
- The firewall therefore advances only to a fresh process-isolated paired panel. This is local official-interpreter evidence, not a hosted score, rank, promotion, or upload claim.

## Mechanism

At step 30, weed continuation converts a route `PASS` into `BUILD_PASTURE`. The rescued pasture later holds a real cow. At step 88 its extra fertilizer sale lets the same market queue cross the $400 threshold for a second cow that baseline cannot fund. That second purchase drives a large supply cascade: TITAN loses five figures of terminal cash, but Apex loses more and the outcome flips to a win.

The firewall keeps the rescued pasture/cow. It suppresses only a later **same-species `BUY_ANIMAL`** when all of these are true:

1. the current pre-market cash cannot fund one animal;
2. an earlier row in the same queue is a `SELL`;
3. the species matches an animal occupying a recorded weed-continuation site.

The queue row becomes `[]`; queue length, every unrelated order, and all unit actions are preserved. This is deliberately narrower than disabling weed continuation.

## Reproduce

The exact package, raw evaluator reports, hashes, materializers, analyzers, witnesses, and 14 tests are stored as a deterministic archive split under `bundle/`.

```bash
python unpack_and_verify.py --output /tmp/titan-weed-evidence --verify
```

The reassembler verifies:

- armored SHA-256 `4c387fc243b78da94dba41c1d3efe0360606e62ccbde27052d9b61bd26eb29e4`;
- archive SHA-256 `89c89ba44ec0841a04e69bcfaa0d4f5209aaaa9e9847b84eaeac76e2c2cf454d`;
- every file in the embedded `SHA256SUMS`;
- the 14 focused/replay contracts;
- byte-identical regeneration of both committed 64-cell reports.

`weed_capital_firewall.py` is also exposed at this level for direct review. The two compact result JSON files are exposed beside it; the bundle remains the authoritative complete receipt.

## Integration boundary

The primitive is evidence-only and default-unwired. It does not edit canonical TITAN, `CURRENT-ARCHIVE`, configuration, provider state, or Kaggle state. A consumer should bind it to the final returned market queue after the weed site has been observed, then run fresh strongest-opponent seeds in sterile processes. Admission must preserve every W/T/L cell before own cash and margin are considered.
