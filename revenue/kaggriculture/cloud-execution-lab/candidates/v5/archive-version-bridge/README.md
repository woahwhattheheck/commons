# V5 exact V3.1 ↔ V4 authenticated archive bridge

Evidence-only tooling for the owner-reported V3.1 > V4 regression. It does **not** thaw V4, change a gameplay default, republish `titan-current`, or copy either legacy policy into production runtime.

## Exact archive authorities

- V3.1: source `a90d888f03987ef0b35cfd20ec3519c6144db08a`, Kaggle submission `56172377`, archive SHA256 `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`.
- V4: frozen source `4af1113154e78c662780e6658cd920daac7902e3`, Kaggle submission `56182437`, archive SHA256 `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`.

The launcher rejects any other archive bytes.

## Direct archive bridge

`bridge.py` reuses the authenticated V5 snapshot helper, extracts each exact submitted archive into a fresh payload per game, writes the standard raw-file adapter to its root `main.py`, and runs the pinned official interpreter plus authenticated Apex v7 / Arlene v14 reference opponents. Its local play loop retains the tested seat's exact returned actions, so pair evidence includes terminal score/margin, canonical action SHA256, first V3.1 ↔ V4 returned-action divergence, trace hash, daily banks, callback/process timing, failures, and source/archive/engine identities.

```bash
KG=/path/to/commons/revenue/kaggriculture
ENGINE=/path/to/pinned-engine
V31=/path/to/titan-v31-a90d888f-submitted.tar.gz
V4=/path/to/titan-v4-4af11131-rebuilt.tar.gz

python3 -B bridge.py \
  --kg-root "$KG" \
  --engine-dir "$ENGINE" \
  --v31 "$V31" \
  --v4 "$V4" \
  --seeds 2051966578 \
  --opponents arlene_v14 \
  --seats 0,1 \
  --output v31-v4-bridge-2051966578
```

This is an offline official-interpreter experiment, **not** hosted Kaggle resource enforcement.

## Reduce the sharded recorded-trace gauntlet into repair hotspots

`reduce_gauntlet.py` consumes existing `gauntlet-top30-union/run.py` output; it does not run games or create another policy carrier. Final authorization is rooted in the **exact corpus index bytes**, not self-reported fixture counts.

```bash
python3 -B reduce_gauntlet.py \
  --index /path/to/top30-union-index.json \
  --v31-root /workspace/shard0/out-v31 \
  --v31-root /workspace/shard1/out-v31 \
  --v4-root /workspace/shard0/out-v4 \
  --v4-root /workspace/shard1/out-v4 \
  --output /tmp/v31-v4-gauntlet-reduction.json
```

The reducer single-reads the supplied corpus index, every `run.json`, and every consumed game JSON from ordinary non-symlink files. Parsing and SHA256 use the same captured bytes. Every raw game source SHA is retained in the authority receipt, so score-bearing evidence changes necessarily change `authority_sha256`.

For each run root it authenticates the exact submitted candidate archive hash and requires the `run.json.index_sha256` to equal the supplied index bytes. It reproduces the producer's `group=all` recorded-trace eligibility and `enumerate(rows) % shards == shard` partition from that index, then requires `selected_fixtures` to equal the independently reconstructed full shard size. A `--limit`-truncated run therefore cannot authorize, even if every shard number is present. Extra opponent IDs are rejected.

The same execution authority must hold across every consumed V3.1/V4 root: canonical corpus index SHA, validated engine hash map, evaluator SHA256, and loader SHA256. Declared shard topology must be consistent, shard IDs unique, and final authorization requires the complete shard set on both versions. Each cell's submission, seed, evaluator-reported `candidate_seat`, family, memberships, recorded orientation, kind, and adaptive flag must match the authenticated index row plus filename-derived tested seat. This binds every score-bearing cell to the exact fixture world and also proves p0/p1 are the same recorded fixture with complementary orientation.

Final panel cardinality is derived from the authenticated corpus: `2 × recorded_trace fixtures`. The current corpus has 123 recorded fixtures, so complete both-seat coverage is 246 cells. `--expected-cells` is only an optional cross-check; a conflicting value fails closed. Partial evidence remains exit `3`/non-authorizing, malformed or cross-wired evidence exits `2`, and only a complete authenticated panel exits `0`.

Outputs include overall, family, submission, and descending per-cell V3.1>V4 `regression_hotspots`, plus the complete evidence authority and digest. That lets the single V5 line repair places where V3.1 actually beats V4 instead of resurrecting historically interesting but inert features.

## Contracts

```bash
python3 -B -m py_compile bridge.py test_bridge.py reduce_gauntlet.py test_reduce_gauntlet.py
python3 -B -m unittest -v test_bridge.py test_reduce_gauntlet.py
python3 -O -B -m unittest -v test_bridge.py test_reduce_gauntlet.py
```

Reducer predecessors cover hotspot ranking, 123-fixture → 246-cell derivation, incomplete shard non-authorization, favorable-subset override rejection, `--limit` truncation, extra corpus IDs, candidate/index/engine/evaluator/loader drift, fixture seed and candidate-seat mismatch, mirrored p0/p1 metadata corruption, duplicate shard receipts, 719-callback enforcement, parse/hash same-capture custody, post-read cell mutation, score-cell tamper changing authority, symlink rejection, and partial CLI publication.


## Canonical corpus + workspace-index authority (v4)

The reducer no longer lets a caller-provided runtime index define the universe.
Authorizing reduction requires `--corpus` pointing at the extracted canonical
Top30-union corpus. The reducer single-reads and pins manifest SHA256
`510ca5c5...`, captures all 123 replay files by the manifest SHA256s into a
private temporary corpus, captured-loads the pinned `corpus.py` Git blob, and
re-materializes the 41 x 3 recorded-action fixtures itself. Runtime index rows
must exactly equal that canonical materialization on fixture identity,
provenance, orientation, replay SHA, action-tape SHA, adapter SHA, and decision
count.

`corpus.py` intentionally records an absolute adapter path, so independent
shard workspaces have different raw `recorded-opponents.json` bytes. `--index`
is therefore repeatable. Each run is bound to the exact raw index SHA it used;
V3.1 and V4 for the same shard must share that raw index, while different
shards may use different raw SHA256s only when their canonical materialization
digest is identical. This preserves every already-running shard without
normalizing or rewriting its evidence.

### Frozen corpus authority

The reducer binds the historical shard panel to immutable `canonical-manifest-510ca5c5438fb65d.json` (SHA256 `510ca5c5438fb65d29755f2009f07bb85bbf3e8963054b88c4abe3ec3737924e`). The live `gauntlet-top30-union/manifest.json` is leaderboard-derived and may advance independently. `--corpus` supplies the pinned materializer plus replay bytes; it cannot redefine the 41-submission / 123-fixture universe.
