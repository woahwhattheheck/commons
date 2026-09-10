# TITAN V3 S13 applicability donor — assembly and custody

**Disposition:** `DONOR_ONLY_COLLISION_RELEASED`

This directory is an additive transport carrier for the already-owned S13 replay-action applicability work. It is rooted directly on replay-identity PR #12052 exact head `5ab2c77d07f8da62b82fe2de85d87ca1e2c9456b`. It changes no canonical runtime, configuration, archive, pointer, game bank, provider, Kaggle, submission, or promotion state.

Earlier durable owners retain custody under Slack timestamps:

- `1789071787.999259`
- `1789071796.419259`
- `1789071828.904339`

The archive's `EVIDENCE.json` records the state at validation time, before this donor-only ref was published. Its `repository_ref_mutated: false` field therefore means that no repository ref had been changed by the validation run; this branch publication is the sole subsequent ref mutation and is non-canonical.

## Reassemble

```bash
cat titan-v3-s13-applicability-donor-sol-audit.tar.gz.part-* \
  > titan-v3-s13-applicability-donor-sol-audit.tar.gz
wc -c titan-v3-s13-applicability-donor-sol-audit.tar.gz
sha256sum titan-v3-s13-applicability-donor-sol-audit.tar.gz
```

Expected archive:

- bytes: `21826`
- SHA-256: `48225d4cc011ed8670d7bc537ae2cb0da652722d600ef411230654490cac3b77`

Part SHA-256 values, in lexical concatenation order:

```text
580721e9902ad5b6f1fd27461a88ac83093b5f8553733a14d3161ad386a6589d  part-00
95574dbcdde86660aee8e1a9af217b815573761e2582a501b652e1aa320cc8c7  part-01
9867df81aba95d4a0795e265e394e40ee641fbce3c3bf597eea23744471da1af  part-02
4d6e45cb9ae5f2c1d6ee961931482b801aab6d898d1177c5d366645549bf4e47  part-03
ffed213d706e597a6f8e9d681e5da66d4c4ce4ca0edcfd68be8e454ff9cd04fe  part-04
5d015158f7177cc6eb30f6595f5b452c02d43607c35224367d2639c0851b93b3  part-05
```

## Validate

```bash
mkdir donor && tar -xzf titan-v3-s13-applicability-donor-sol-audit.tar.gz -C donor
cd donor/titan-v3-s13-applicability-donor-sol-audit
sha256sum -c MANIFEST.sha256
KAGGRICULTURE_ENGINE=/absolute/path/to/pinned/kaggriculture.py \
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
python -B -m unittest -v \
  test_public_state_applicability.py \
  test_official_engine_parity.py
```

Pinned official engine SHA-256: `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.

Validated evidence: 49/49 unittest cases; 47 adversarial contracts plus 20,000 deterministic single-actor and 20,000 deterministic multi-actor exact-engine transition comparisons. The audit repaired MELON's maximum-yield WATER boundary from day 10 to day 12 and rejected every immature HARVEST, including one-time crops.

This carrier makes no score, promotion, opponent-equivalence, future-route-equivalence, or official-engine-source-binding claim. Consume its predecessor cases and differential harness inside the earliest owner's exact transition gate.