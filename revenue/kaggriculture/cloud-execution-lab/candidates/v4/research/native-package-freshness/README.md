# Native package freshness gate

`check_native_freshness.py` closes one narrow execution-evidence gap: an artifact may be internally authenticated yet stale relative to the exact canonical checkout used to call it **current**.

The gate is read-only and policy-inert. It never builds, extracts, publishes, rewrites, activates, or promotes a TITAN package. It authenticates the supplied tar bytes, binds the live production core to an exact Git `HEAD`, and compares exactly five execution-critical package members:

- `main.py`
- `titan_runtime.py`
- `scheduler.py`
- `frozen_selected.py`
- `TITAN-CONFIG.json`

The output verdict is `CURRENT` only when all five package members are byte-identical to the same files tracked by the caller's exact `HEAD`. Any difference is `STALE`; malformed/untrusted evidence, dirty live bytes, symlinked live/core members, duplicate or missing tar members, hash drift, or commit drift is `INVALID`.

Example:

```bash
python check_native_freshness.py \
  --repo-root "$GITHUB_WORKSPACE" \
  --archive /tmp/titan-current.tar.gz \
  --expected-archive-sha256 <authenticated-tar-sha256> \
  --expected-commit "$(git rev-parse HEAD)"
```

Exit codes are `0=CURRENT`, `1=STALE`, and `2=INVALID`. JSON is deterministic and includes exact SHA-256 + Git-blob identities for both live and packaged core members.

## Boundary

This is an execution-admission theorem, not a package publisher or gameplay mechanism. The active current-native refresh owner retains artifact construction/custody. FASTTAPE and other package families retain their own semantic rebinds. `COMPOSITION.json`, `INTEGRATION.json`, production runtime/default/config bytes, archives, and Kaggle surfaces are outside this package.

## Historical motivating witness

Authenticated artifact `10180428228` / tar `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9` has package core blobs `main.py=4a8cf7bc…`, `scheduler.py=a483b24d…`, `frozen_selected.py=fc7baf5c…`, `TITAN-CONFIG.json=3a3bef83…`, but `titan_runtime.py=b952c9c2…`. At construction base `44af4a1d…`, canonical live runtime is `6d9720f4…`; therefore that authenticated package is `STALE`, not current. The gate is general and does not special-case those identities.
