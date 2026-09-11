# TITAN V3 S17 optimization-safe exact-tree repair series

Operation: `TITAN-V3-S17-OPTIMIZATION-SAFE-EXACT-TREE-COMPOSITION-20260910-01`

This exact-base repair series is a durable, directly applicable successor to the
authenticated S17 one-tree source handoff while its separate landing workflow remains
runner-queued. It is based on Git commit
`14dbbc4940262790f7e21c0bdc7a941842f238ba` and consumes Slack object `F0C1076QWK0`
(68,057 bytes; SHA-256
`5b0559f07c0d2abfdc21b85362472cb848bd43555f1fcf5a67230192adfc6616`).

## Apply

From the root of that exact 18-file S17 source tree:

```bash
git apply /path/to/titan-v3-s17-optimization-safe-tree/patches/*.patch
```

The seven ordered patches reconstruct the complete 22-file hardened tree byte-for-byte.
`SERIES.json` pins their order, byte lengths, and SHA-256 digests; its own SHA-256 is
`2994447565c3830fbbc3c3e9b4528cb6d31c8179b9944616bc6bb2a4734c4b81`.
The series was applied to a fresh copy of the authenticated input and the resulting file
inventory and every file digest exactly matched the independently built hardened tree.

## Repair content

The successor removes all eight optimization-removable correctness assertions from
`build_v3.py` and `apply_v3.py`, preserving exact output for the clean canonical input.
Exact-once anchors, canonical/archive/source/FILES receipts, and duplicate configuration
keys now fail through explicit exceptions under ordinary Python and `python -O`.
Configuration insertion preflights every V3 key before mutation, so a collision cannot
leave a partially edited object.

It also composes SOL-CLEANROOM PR #11990's exact and atomic `--tree` publication semantics:
canonical relative POSIX member names only; no stale, file, or symlink target; adjacent
staging; byte-for-byte staged readback; one final rename; and cleanup on failure.

## Verification completed before publication

- exact 18-file input safely inventoried: pass
- seven-patch series reapplies to an exact 22-file tree: pass
- Python compilation: pass
- hardening contracts: 13/13 pass
- the same contracts with `PYTHONOPTIMIZE=1`: 13/13 pass
- GitHub Actions YAML parse and every shell run block: pass

`S17-HARDENING-RECEIPT.json` records the bound input, pre/post source hashes, composition
inputs, expected package receipt, and non-goals. SHA-256:
`581cbad954c8fcb07b05567cb1300737313f27ed0f757e7dafea9d03dcbaf3bb`.

The workflow `.github/workflows/titan-v3-s17-optimization-safe-tree.yml` verifies the
series, fetches `v3/rebase-14dbbc49-20260910-01`, and—once that branch exposes
`candidates/v3`—applies the repair and runs both 13-test modes, the canonical rebuild,
122-file exact-tree closure, and all 54 S17 package tests. Until then it records the
canonical composition gate as **deferred, not passed**. Workflow SHA-256:
`49e892849801024b13ce8f448c5dc30fe75072b271e4fa97105a218eb1aafaeb`.

The remaining environment-bound gate targets package SHA-256
`6766c55a80b4cfc95232dd219a11b701121cd21935da5bb38a76dd90bbb9fd5f`.
No canonical-build, package-test, score, or promotion result is represented as passed
until the corresponding workflow steps actually execute.

## Scope

No gameplay lane, shipped feature default, canonical archive, expected package bytes,
package pointer, provider state, Kaggle submission, score, or promotion disposition is
changed or claimed. This series is intended for direct consumption by the S17 landing
owner and T08 integration spine without waiting for a GitHub runner to rewrite another
branch.
