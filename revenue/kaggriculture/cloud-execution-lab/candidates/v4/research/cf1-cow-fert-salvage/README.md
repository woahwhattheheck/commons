# CF1: COW empty-HARVEST fertilizer salvage

Status: implemented and locally mechanism-tested; inactive research component in canonical main:candidates/v4. This is not a production key, release, economic promotion, or Kaggle submission.

## Mechanism and proof boundary

At a complete day's hour-23 callback (through step 695), rewrite exactly one already-empty COW HARVEST into COLLECT_FERTILIZER. The COW must already be fed and cared for, with fertilizer available. Full reconstructed actor/action/inventory vectors, strict standard configuration, an unstacked target, nonproducing sibling commands, a SELL-only executable market prefix, and total shed + all carried cargo + 1 <= 100 are required. All no-match/OFF paths preserve exact parent action identity.

Executed synthetic differential fixtures show the unchanged pinned interpreter ends the callback with exactly one extra own shed FERTILIZER and otherwise identical public/market/cash/private state. A forced unsafe full-shed fixture demonstrates why the guard is necessary: extra fertilizer can displace existing MILK during EOD deposit. This is one-step preservation, not a proof of future profit: the extra stock may crowd later purchases or change later policy decisions.

## Reproduce

Supply the exact original Kaggriculture engine Git blob 3c202c7ee921da239356789e266b694635103fc4 (SHA256 bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e). The executed copy was recovered from existing workflow artifact 10285621024, member seed-retry-runtime/checks/reference/engine/kaggriculture.py; no new Actions run was dispatched.

From this directory:

```sh
python check_cow_fert_salvage.py --engine /absolute/path/kaggriculture.py -v
python -O check_cow_fert_salvage.py --engine /absolute/path/kaggriculture.py -v
```

Both modes pass 19 tests, including 348 synthetic full-interpreter state pairs (29 complete days x 2 seats x farmer/hand x 3 stock/cargo cases). No gameplay function is stubbed. The unused seed-resolution import is replaced with a fail-on-use bootstrap shim because these fixtures start from explicit initialized state. This does not test initial game setup. The check filename intentionally avoids automatic generic test discovery because it requires an explicit pinned-engine argument; source bytes are unchanged from the tested test_cow_fert_salvage.py donor.

## Integration and next gate

Keep this experimental helper out of overlay/config until actual current-V4 engagement is measured. First instrument a full reconstructed parent action, including the hidden fertilizer hand. Zero natural activations closes the lane; never synthesize profitable activations. On positive engagement, run paired complete games with both seats and exact current parent, recording actual recovered units, final own/rival cash, worst margin regression, and subsequent shed-capacity/purchase effects.

The future single key is r04_cow_fert_salvage, with literal-OFF defaults. Place any eventual transform after whole-agent hand reconstruction and before downstream EOD/storage-sensitive transforms, then rerun composition tests; this document alone is not final ordering authority. Do not preempt productive HARVEST or broaden to feeding/CARE or GC5 productive-harvest skipping. Do not create another V4 branch or duplicate controller.

## Canonical destination and ABI boundary

Canonical marker 00142be0ff2314dcb23068c8133b34d290661923 names main and revenue/kaggriculture/cloud-execution-lab/candidates/v4 as the sole integration line. These files belong under research/cf1-cow-fert-salvage/. Old V4 refs are donor evidence only; no old ref was updated by this delivery.

Current production uses the newer frozen/ordered/parent runtime, not the old R04 materializer ABI. Preserve this source and its tests, then bind any actual evaluation to the exact current parent and full observation/action contract. Never execute the legacy apply_v4 against the production root to install this experiment. No production runtime, shared materializer, overlay, config, workflow, or archive file is modified here. No full package rebuild, field score gate, or runtime activation is claimed.

Exact tested source identities and results are in RECEIPT.json. Author of this lane: ASTRA/DELTA.
