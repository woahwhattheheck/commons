# Fixed Evidence Freshness Diagnostic

This package commercializes the already-merged `revenue.multi_framework_evidence_freshness` classifier as a bounded buyer-safe diagnostic. It does **not** fork or reinterpret the underlying classifications: production compilation calls the merged engine's public `compile_packet()` and immediately re-verifies the resulting packet through public `verify_packet()`.

## Offer boundary

- fixed diagnostic hypothesis: **$3,500** for one sanitized export containing **1–500 evidence objects**;
- optional integration sprint hypothesis: **$10,000**, only after the paid diagnostic establishes value and actual adapter scope;
- **no free custom adapter**;
- commercial state is always `PROPOSED_NOT_ACCEPTED` until a separate provider/customer receipt says otherwise.

The request must explicitly set `sanitized_export_attested: true`. The engine retains its strict opaque-reference, checksum, mapping, freshness, temporal, and secret-shaped-reference controls.

## What the diagnostic emits

The compiler creates three create-exclusive artifacts:

1. the complete underlying engine packet;
2. a buyer-safe diagnostic JSON with aggregate state counts, aggregate non-reusable reason counts, the code-owned offer, and exact bindings to the request, normalized engine input, engine packet, projection, engine Markdown, engine receipt, engine source bytes, and wrapper source bytes;
3. a concise Markdown report containing aggregate counts/reasons and evidence hashes but **no per-evidence IDs**.

Verification re-runs the underlying engine's current-freshness verifier, recompiles the request through the public engine to prove request→packet input binding, reconstructs the diagnostic, verifies its receipt, and requires byte-identical Markdown.

## CLI

```bash
python -m revenue.multi_framework_evidence_freshness_pilot.cli compile \
  request.json engine_packet.json diagnostic.json buyer_report.md

python -m revenue.multi_framework_evidence_freshness_pilot.cli verify \
  request.json engine_packet.json diagnostic.json buyer_report.md
```

Inputs are bounded regular UTF-8 JSON with duplicate keys and non-finite numbers rejected. Final-component input symlinks fail closed where `O_NOFOLLOW` is supported. Outputs are created relative to a retained final parent-directory descriptor with `O_EXCL`/`O_NOFOLLOW`; a late output collision is fail-visible and preserves earlier successfully published files rather than deleting by pathname.

## Authority ceiling

This is deterministic read-only evidence-freshness QA. It is **not** an audit opinion, certification opinion, control-effectiveness conclusion, assurance of evidence authenticity, or proof that evidence is sufficient. It has no authority to contact a customer/assessor, mutate evidence, mutate provider/account state, accept payment, recognize revenue, or send outbound messages. Human owners retain those decisions.

## Validation

```bash
python -m py_compile \
  revenue/multi_framework_evidence_freshness_pilot/pilot.py \
  revenue/multi_framework_evidence_freshness_pilot/cli.py \
  tests/test_multi_framework_evidence_freshness_pilot.py
python -m unittest -v tests.test_multi_framework_evidence_freshness_pilot
python -O -m unittest -v tests.test_multi_framework_evidence_freshness_pilot
```

The tests patch only the existing engine's internal clock for deterministic historical fixtures; production calls remain on the public current-time compiler/verifier.
