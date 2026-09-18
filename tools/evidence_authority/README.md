# Source-bound Evidence Authority Kernel

This package is the reusable boundary behind provider/buyer/issuer claims that must **not** become authoritative merely because a caller writes an authority label, a plausible hash, or a local path.

## Trust model

The caller supplies a candidate claim, but the candidate schema contains no authority class and no trusted root. Positive authority comes only from a separately supplied, out-of-band pinned SHA-256 of a canonical authority manifest. The manifest is a closed inventory of canonical relative source paths plus exact source-byte SHA-256 values. The runtime requires the supplied source mapping to match that inventory exactly: no missing source, extra source, duplicate path, alias path, or digest drift is accepted.

Each retained source is itself canonical JSON and carries the authority record: authority class, issuer, subject, claim kind, scope, generation, issued/observed/validity times, and canonical claim payload. The kernel derives an `authority_fact` from those retained bytes. The candidate may name a record and expected claim identity, but cross-account/counterparty/scope/kind/generation/payload transplants HOLD.

`compile_current()` owns process UTC and captures its validation/hash/clock policy generation when the supported API is constructed, so ordinary post-import module-global helper/constant rebinding cannot widen an already-created compiler/verifier pair. A retained fact is current only when its issued/observed time is not future, its optional validity has not expired, and its observation age fits the pinned manifest's `max_age_seconds`. `compile_integrity()` deliberately emits historical integrity only and can never set `current_authority=true`. `verify_receipt()` exact-replays a historical/current receipt but returns an all-false current/external authority envelope; callers needing a current decision must call `compile_current()` again now.

Every receipt permanently keeps `external_side_effects_authorized=false`. This package does not send messages, create provider sessions, deploy, authorize spend, make payments, or establish accounting/revenue truth.

## Strict boundary

JSON is bounded and canonicalized with duplicate-key rejection, strict UTF-8 scalar text, no floats/NaN/Infinity, bool/int separation, bounded integers, depth/nodes/containers/string bytes, and a 256 KiB per-document ceiling. Retained manifests and retained source records must already be byte-exact canonical JSON. The complete retained source set is capped at 2 MiB and 64 manifest entries.

## CLI

The fixture is synthetic/redacted and contains no credential or real account identity.

```bash
ROOT=$(cat tools/evidence_authority/fixtures/pinned_root.txt)
python -m tools.evidence_authority.cli compile-current \
  tools/evidence_authority/fixtures/candidate.json \
  tools/evidence_authority/fixtures/manifest.json \
  tools/evidence_authority/fixtures/sources "$ROOT" > /tmp/authority-receipt.json

python -m tools.evidence_authority.cli verify \
  tools/evidence_authority/fixtures/candidate.json \
  tools/evidence_authority/fixtures/manifest.json \
  tools/evidence_authority/fixtures/sources "$ROOT" /tmp/authority-receipt.json
```

The first command can emit `CURRENT_AUTHORITY` for the synthetic retained record while the second returns only receipt integrity (`current_authority=false`). `compile-integrity` is available for historical evidence processing and is never current-positive.

## Provider-cost migration donor

`provider_cost_example.py::compile_provider_cost_authority()` demonstrates the intended composition: downstream provider-cost logic calls this kernel over a pinned retained source generation and consumes the derived source-bound fact plus authority receipt digest. It must not accept raw caller JSON saying `authority="PROVIDER_AUTHENTICATED"`. This is an adapter example only; it does not mutate or take custody of the active provider-cost product.

## Tests

```bash
python -m unittest -v tools.evidence_authority.test_kernel tools.evidence_authority.test_integration
python -O -m unittest -v tools.evidence_authority.test_kernel tools.evidence_authority.test_integration
python -m py_compile tools/evidence_authority/*.py
```

Hostiles cover self-auth labels/root injection, retained-source rewrite and self-hash, closed-inventory shrink/expansion, path aliasing, subject/scope/kind/generation/payload transplant, stale/future/expired currentness, caller-time backdating, cross-generation replay, duplicate JSON keys, huge ints, float/nonfinite input, lone surrogates, bool numeric aliasing, receipt rehash laundering, source-loader/clock/policy/hash module rebinding, descriptor/path symlink substitution, and manifest/record duplication.
