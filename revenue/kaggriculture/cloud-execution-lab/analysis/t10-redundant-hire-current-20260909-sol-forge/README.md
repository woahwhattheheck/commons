# TITAN T10 redundant-hire — exact `a055` disposition

This packet answers one narrow regression question: did the enabled T10
`redundant_hire` transform make the exact canonical archive at dispatch weaker
than identical bytes with that one feature disabled?

## Result

**KEEP T10 enabled for this tested archive.**

The fail-closed grid contains 80 complete official-interpreter development
games: five opponent policies (`v1`, Arlene, Apex, Kaito, Reyhan), four seeds,
and both candidate seats, for 40 exact treatment/control pairs.  Enabling T10
changed all 40 traces and improved every paired margin:

| Measure | Enabled minus disabled |
|---|---:|
| Mean own cash | **+5.4** |
| Mean rival cash | +0.1 |
| Mean margin | **+5.3** |
| Minimum paired margin | **+5** |
| Maximum paired margin | **+11** |
| Verdicts | 40 W→W |

An instrumented Arlene pair showed the active mechanism: at step 121 T10
removed one physically redundant trailing hire, saving exactly 5 cash.  The
speculative productive-detour path activated zero times in that probe.  This
packet therefore rejects a blanket T10 revert; it does **not** certify the
unexercised detour on every possible state.

## Bound identities

- Archive SHA-256: `a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba`
- SOURCE.json SHA-256: `b96676977687ee8a92d7213380f96bf5774a5ec26925cb4f0d66bdd244eb44ba`
- Official engine ref: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`
- Canonical-check workflow run: `34390450538`; artifact: `10119413771`
- Seeds: `2609097001`–`2609097004`
- Only experimental factor: `TITAN-CONFIG.json.redundant_hire = false/true`

`MANIFEST.json` binds the archive, source, engine, evaluator, loader, opponent
entry files and opponent directory trees. `SUMMARY.json` retains all 80 game
rows and every 40-cell paired delta.

## Verify

From this directory:

```bash
python -B verify_evidence.py --json
python -B -m unittest -v test_verify_evidence.py
```

To additionally re-hash locally recovered inputs:

```bash
python -B verify_evidence.py \
  --archive /path/to/a055/titan-current.tar.gz \
  --source-manifest /path/to/extracted/SOURCE.json \
  --gauntlet-root /path/to/titan-v1-predecessor-public-policy-gauntlet-20260909
```

The verifier rejects summary byte swaps, duplicate JSON keys, missing or
duplicated game cells, bad arithmetic, invalid trace hashes, forged aggregates,
non-positive paired deltas, verdict regressions, and optional external-source
drift.

## Limits

This is offline development evidence, not hosted Kaggle scoring, a first-place
estimate, holdout authority, or permission to move the canonical archive or
submit externally. The repository's canonical pointer moved after this panel;
all claims here remain scoped to the exact `a055fd56…` bytes named above.
