# TITAN V3 one-tree integrity review

Operation: `TITAN-V3-ONE-TREE-INTEGRITY-REVIEW-20260910-01`  
Input: Slack `F0C1403CASG`, `sha256:5594d47338368069308077c9a0ce400d473fab5172d01d93235176283fd833a9`  
Canonical base: `sha256:17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`

This is a review carrier, not a competing publication lane. The durable one-tree owner retains rebase, merge, feature-promotion, panel, and submission custody.

## Predecessor-killing findings

The exact superseding repin builds reproducibly as `16313449ff89061dc3a3193a78240161a5811a385f3ff30af4a09f82102707c7` (443,513 bytes, 117 files), but its in-package `SOURCE.json` remains the 109-member canonical source map after the builder adds seven overlay files and transforms five canonical files. Exact audit: seven members are absent from the manifest and five declared members have different bytes or hashes.

L01 also edits `controller.R` in place after route-derived owners are constructed. Arlene's `routes()` returns one cached process-global graph. Enabling LEANPLANT mutates 321 tape actions, reducing MAIN WHEAT plants from 164 to 72; every later all-off agent in that interpreter sees the contaminated 72-tape state. The original 35 tests run all-off before feature-on and cannot detect that transition.

## Patch

`titan-v3-one-tree-integrity.patch.gz` expands to a patch that applies seven source changes on top of the exact 13-path repin:

- preserve canonical provenance at `reference/v3-base/SOURCE.json`; generate and validate a truthful top-level V3 `SOURCE.json` after all transforms;
- bind final member set, byte count, SHA-256, source lineage, base archive, apply script, builder, overlays, default-off state, and non-submission status;
- reject unsafe or duplicate canonical archive members and replace release-critical `assert` gates with explicit exceptions;
- clone the cached route graph before L01 tape edits and before SeedBudget/spatial owners capture it, retaining shared-prefix identity inside each private clone;
- make O01/E20 composition transactional, including restoration after an in-place first-stage mutation followed by a downstream exception;
- add four predecessor-discriminating contracts: enabled→off contamination, two enabled-agent isolation, exact package-source closure/base preservation, and downstream rollback after in-place mutation.

## Local exact-byte proof

```text
V3 BUILD 07e9163000f8180cfebe23acc18e230565fc53f2de8611cfda44c6370ef317b6 119 files 454278 bytes
V3 CHECK OK 07e9163000f8180cfebe23acc18e230565fc53f2de8611cfda44c6370ef317b6 119 files 454278 bytes
Ran 40 tests in 0.973s
OK
```

All V3 keys remain off. No game, score, promotion, provider, Kaggle, or submission claim is made for these bytes.

Apply from the repository root after the exact 13-path repin is present:

```sh
gzip -dc analysis/titan-v3-one-tree-integrity-review-20260910-01/titan-v3-one-tree-integrity.patch.gz | git apply --check -
gzip -dc analysis/titan-v3-one-tree-integrity-review-20260910-01/titan-v3-one-tree-integrity.patch.gz | git apply -
```

Patch SHA-256 after decompression: `a7c39a82d9912b6d2570d989a84c5d0fe819058e97618761838074b418ecfab4`; 67,573 bytes. Compressed carrier SHA-256: `ac32fd74e9d1587f94e1e6e3304b1913c3811b06e0ebe607bf8ed72d982d523a`; 16,249 bytes. See `RECEIPT.json` for the machine-readable boundary.
