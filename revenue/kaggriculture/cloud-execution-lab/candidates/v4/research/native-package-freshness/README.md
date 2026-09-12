# Native package freshness gate

`check_native_freshness.py` closes one execution-evidence gap: an artifact may be internally authenticated yet stale relative to the exact canonical checkout used to call it **current**.

The gate is read-only and policy-inert. It never builds, extracts, publishes, rewrites, activates, or promotes a TITAN package. It authenticates the supplied tar bytes, requires the canonical live production root `revenue/kaggriculture/cloud-execution-lab`, binds that checkout to an exact Git `HEAD`, strictly parses the package's own `SOURCE.json.runtime` receipts, and compares **every declared runtime package member** to the exact tracked source byte named by that receipt.

The five historical core files remain mandatory and source-path-bound:

- `main.py`
- `titan_runtime.py`
- `scheduler.py`
- `frozen_selected.py`
- `TITAN-CONFIG.json`

But they are no longer the whole freshness theorem. `titan_runtime.py` loads behavior-relevant helpers outside that set, so a five-file-only comparison can falsely call a package current while an imported dependency is stale. The v2 gate therefore treats the authenticated `SOURCE.json.runtime` mapping as the package source-closure manifest and requires exact member-set, byte-count, SHA-256, normalized source-path, tracked-HEAD, and live-byte agreement.

`CURRENT` means the complete declared source closure matches the exact checkout. Any declared member difference is `STALE`. Malformed/untrusted evidence, dirty live bytes, a noncanonical `--live-dir`, archive/member symlinks, duplicate/nonregular/extra/missing members, manifest hash/size/path drift, non-finite or duplicate-key JSON, source paths escaping the repository, archive hash drift, or commit drift is `INVALID`.

Example:

```bash
python check_native_freshness.py \
  --repo-root "$GITHUB_WORKSPACE" \
  --archive /tmp/titan-current.tar.gz \
  --expected-archive-sha256 <authenticated-tar-sha256> \
  --expected-commit "$(git rev-parse HEAD)"
```

`--live-dir` remains accepted for interface compatibility but only the canonical production directory is valid. Exit codes are `0=CURRENT`, `1=STALE`, and `2=INVALID`. JSON is deterministic and reports exact SHA-256 + Git-blob identities plus the manifest-resolved tracked `source_path` for every declared runtime member.

## Predecessor killers

Two false-green constructions are explicitly rejected:

1. A tracked decoy directory containing package-matching copies cannot be supplied as `--live-dir`; noncanonical roots are `INVALID`.
2. A package whose five core files match but whose declared imported helper (for example `spatial_tempo.py`) is stale is `STALE`, not `CURRENT`.

The same code was also exercised against the authenticated historical b567 package shape: all **109** declared runtime members classify `CURRENT` in a reconstructed byte-identical checkout; committing a newer `spatial_tempo.py` alone changes the verdict to `STALE` with that single member reported.

## Boundary

This is an execution-admission theorem, not a package publisher or gameplay mechanism. The active current-native refresh owner retains artifact construction/custody. `SOURCE.json` is consumed only after the caller authenticates the whole tar digest; this checker does not mint package provenance. Conservative whole-package staleness is intentional: a false `STALE` can trigger a refresh, while a false `CURRENT` can contaminate evidence. FASTTAPE and other package families retain their own semantic rebinds. `COMPOSITION.json`, `INTEGRATION.json`, production runtime/default/config bytes, archives, and Kaggle surfaces are outside this package.

## Historical motivating witness

Authenticated artifact `10180428228` / tar `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9` is the concrete stale-package witness that motivated v1: its packaged `titan_runtime.py=b952c9c2…` differed from canonical live runtime `6d9720f4…` at construction base `44af4a1d…`. V2 preserves that theorem and extends freshness to the package's complete declared source closure; it does not special-case those identities.
