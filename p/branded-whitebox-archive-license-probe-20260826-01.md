# White Box archive GGUF license probe — LANDED

From: `BRANDED: Dissident - shameful`

Date: 2026-08-26

## Exact implementation

- Integrated current-main commit: `f0b77b43e46b36b10f268eaf61ec8751a5f0ec23`
- Expected parent: `27294b0bff70af457f8f28cc560ea6a83689ad4a`
- `host/whitebox_archive_license_probe.py`: blob `2ce1fc3f1da61cf93e21a6971cedc93a7b2df053`
- `revenue/ip/whitebox_archive_license_probe.schema.json`: blob `ae6a5c084b65dfdb0591bb6d9914333397946657`
- `revenue/ip/whitebox_archive_license_probe.json`: blob `c65c2ee0dd491f71f89341f1bbd085a37cb7a1ec`
- `test_whitebox_archive_license_probe.py`: blob `8ce7bdb8e22c80591bfdf870ac2d1e526d35a538`
- Bound inventory blob: `dfc9923c290837151454b086df1af25aed724330`.
- Bound archive tree SHA-256: `d67234a1e0d69dba621f4073ecfbaf77db298134d3bd516fba30fc2062467bc9`.

## Measured source metadata

- All eight original GGUF filenames were located: seven on the normal models route and the existing SmolLM2 original on its `_removed` by-route.
- The eight source files total `140,828,486,272` bytes. No tensor bytes were loaded and no full-model hash was claimed.
- The exact measured region is the GGUF header, metadata, tensor index, and alignment prefix: `60,094,112` bytes total, with one SHA-256 per model.
- Embedded license metadata is present for `7/8`: `apache-2.0` on two, `gemma` on three, `llama3.3` on one, and `mit` on one.
- Mixtral's local GGUF has no embedded license key. The official `mistralai/Mixtral-8x7B-Instruct-v0.1` Hugging Face model API reports `apache-2.0` at revision `eba92302a2861cdc0098cc54bc9f17cb2c47eb61`; the probe marks this `BASE_MODEL_PRIMARY_SOURCE_ONLY`, not proof of the local quantized copy's provenance.
- Phi-4's local GGUF embeds both `mit` and its upstream license link. Three other GGUFs embed base-model repository URLs; these are recorded exactly but do not identify the quantizer/source copy.
- No absolute local source path is published.

## Commercial truth

- Exact quantized-copy source provenance: not verified.
- Upstream terms and notice obligations: not reviewed.
- Transfer cleared: `false`; archive license offer ready: `false`; pricing ready: `false`.
- Remaining evidence is exact: content-addressed quantized-copy provenance, upstream terms/notice review, and the already-recorded archive redaction/manual-sample review.

## Verification

- Deterministic local rescan: byte-identical probe blob `c65c2ee0dd491f71f89341f1bbd085a37cb7a1ec`.
- `python -W error -m unittest -v test_whitebox_archive_license_probe.py`: `9/9 PASS`.
- Synthetic GGUF fixture proved metadata-prefix hashing excludes tensor-tail mutations and caught/fixed explicit-alignment parsing before landing.
- CLI validation returned `VALID`, `8` models, `7` embedded license IDs, `1` missing, and transfer `false`.
- Exact current-main Draft-2020-12 validation, `py_compile`, diff check, open-door guard, ancestry, and remote blob readback passed.
- No archive payload, model tensor, existing inventory, grants, Outcome Commerce, patent, or TITAN path was changed. No Cursor was used.

## Owner need

None recorded. The remaining work is source/terms evidence and redaction, not a permission question.
