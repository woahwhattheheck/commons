# TITAN V3 one-tree transport custody — exact stale-repin HOLD

Operation: `TITAN-V3-ONE-TREE-TRANSPORT-CUSTODY-20260910-01`  
Owner: `SOL-PRO`  
Input: Slack file `F0C0JPCAAQP`, `v3_candidates_657b3d9c.tar.gz`

## Result

**HOLD_STALE_REPIN. Do not consume this exact transport as a current-main one-tree package.**

The authenticated Slack object is exactly 27,500 bytes with SHA-256
`f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728` and contains
13 regular files under `revenue/kaggriculture/cloud-execution-lab/candidates/v3/`.
Its source-overlay hashes are internally consistent. The defect is a provenance split,
not random corruption:

| field | packet observes | publication thread advertises |
|---|---:|---:|
| canonical archive SHA-256 | `a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba` | `17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86` |
| canonical archive bytes | 423,575 | 427,870 |
| canonical runtime files | 108 | 110 |
| V3 archive SHA-256 | `1d590a3dc65c51a2cd0c94fb59bf34d713e981173ac6436f8cadfab791f7ffac` | `16313449ff89061dc3a3193a78240161a5811a385f3ff30af4a09f82102707c7` |
| V3 archive bytes | 438,079 | 443,513 |
| V3 runtime files | 115 | 117 |

`FINDING.json` is the deterministic, self-sealed raw-read result. Its receipt SHA-256 is
`fb884a71801a26a6d2fe21607928d66c63612b3863896ff2d35a5896f8c31326`.

This is a hard publication boundary because exact-string patch anchors, runtime closure,
`FILES.json`, source pins, tests, and any later gameplay evidence are all interpreted
relative to the canonical package named by `V3-MANIFEST.json`. A packet cannot inherit a
newer base merely because a surrounding Slack message names it.

## Delivered gate

`audit_transport.py` provides two deliberately separate modes:

```bash
# Raw custody reproduction. Exit 3 is the expected HOLD for this object.
python -B audit_transport.py \
  --packet /path/to/v3_candidates_657b3d9c.tar.gz \
  --file-id F0C0JPCAAQP \
  --output RAW-REPORT.json

# Hosted verification of the checked-in immutable finding.
python -B audit_transport.py --verify-finding FINDING.json
```

Raw mode fails closed on transport byte/hash drift, invalid gzip/TAR, duplicate names,
absolute/traversal/backslash paths, links or devices, out-of-root files, oversized input,
missing files, duplicate/non-finite JSON, boolean-as-integer pins, malformed SHA-256,
`FILES.json` cardinality mismatch, and overlay-source digest mismatch. It returns:

- `PASS` only when raw transport, internal manifests, and the advertised current pins all agree;
- `HOLD_STALE_REPIN` when the exact transport is structurally valid but names a different base;
- `INVALID` for corruption, ambiguity, or malformed custody.

The report is canonical-JSON sealed and written by create-plus-atomic-replace. The test
suite contains 17 contracts; hosted CI runs 16 and explicitly skips only the raw Slack
object. Local raw reproduction runs all 17.

## Required successor

Publish a **new** Slack object whose own `V3-MANIFEST.json`, `FILES.json`, source hashes,
and rebuilt archive fields bind the same current base and output identities. Do not mutate
or relabel `F0C0JPCAAQP`. The successor should run this gate in raw mode and receive
`PASS` before source review, one-tree composition, or any official-engine panel spends a
single game.

## Truth boundary

This lane adds analysis, tests, a retained receipt, and CI only. It changes no gameplay
source, candidate key, canonical archive, release pointer, configuration, provider,
Kaggle submission, or leaderboard state. It makes no playing-strength claim. A corrected
transport still needs all-off identity, transactional overlay safety, returned-action
activation, matched official games, candidate-own cash improvement, nonnegative
opponent-by-seat strata, and zero new losses before promotion.
