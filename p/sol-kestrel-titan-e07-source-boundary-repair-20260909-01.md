# SOL-KESTREL — TITAN E07 BUY_PRODUCT source-boundary repair

Operation: `TITAN-E07-BUY-PRODUCT-SOURCE-BOUNDARY-REPAIR-20260909-02`
Workflow run: `34389359021` attempt `1`
Cloud checkout before publication: `6a66c95f5513a0ec97edd3a6f2dc7b8e55b84f15`

## Repair

`fund_same_turn_acquisition` now limits candidate SELL sources to the half-open interval after the failing fixed acquisition and before the first later `BUY_PRODUCT` hard boundary. A variable-price purchase therefore cannot be crossed while a safe pre-boundary SELL remains eligible.

## Discriminating contracts

- target index 1, `BUY_PRODUCT` barrier index 2, SELL source index 3: unchanged queue, `no-safe-prefix-sale`, exact sale quantities preserved;
- target index 1, SELL source index 2, `BUY_PRODUCT` barrier index 3: the safe sale still funds the fixed acquisition without moving either purchase.

## Verification actually run

- Python compilation for the source and focused test;
- `test_e07_hosted_source_path`;
- `test_e07_same_turn_funding` (source semantics before rebuild, canonical binding after rebuild);
- `test_joint_market_slots`;
- `test_e10_floor_cycle`;
- deterministic `build_integrated.py` and `build_integrated.py --check`;
- `test_release_consistency`;
- `test_build_publication`.

## Release identities

- previous current archive preserved as `exports/historical/titan-385022ff9d5c153b09086f261197de9ae502ca57731e00ffd9391c5a6cf39492.tar.gz`;
- new current archive: `a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba` / `423575` bytes / `107` runtime files;
- current source manifest: `b96676977687ee8a92d7213380f96bf5774a5ec26925cb4f0d66bdd244eb44ba`.

No official games, Kaggle/provider action, submission, rank, or playing-strength claim was made. This is a fail-closed market-order correctness repair.
