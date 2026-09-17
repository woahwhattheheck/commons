# INPRS RFP 26-04 — file-backed acceptance handoff

This layer closes the gap between a self-consistent normalized migration bundle and the **actual bytes** a qualified CLM prime would hand over for independent acceptance. It does not make Token Junkie Labs a CLM prime and does not claim INPRS acceptance.

## Trust boundary

`file_backed_acceptance.py` requires four independent inputs: a source manifest, the SHA-256 that an independent source/reviewer pinned for that manifest, a normalized candidate bundle, and a handoff root containing the actual files. The manifest must be canonical JSON. Passing a newly recomputed manifest hash beside a changed manifest is not evidence; the expected hash must come from the separately frozen source-export/review boundary.

The pinned manifest binds the exact contract/vendor set, source-side semantics, source path/hash/size, fixed target/version/public paths, and publication classification. Verification then rereads the actual source, target, version-history, redaction-attestation, public, and internal-vendor files. It rejects row drops, semantic relabels, changed or missing bytes, path traversal/symlinks, duplicate path use, version drift, unexpected public files, and public exposure of internal vendor/attestation bytes. The existing `verify_bundle.py` semantic gate must also pass.

The receipt is path-independent canonical JSON and always keeps `buyer_contact_authorized`, `proposal_submission_authorized`, `contract_acceptance_authorized`, `payment_authorized`, and `revenue_recognition_authorized` false.

## Synthetic executable handoff

The demo contains no INPRS or vendor data:

```bash
python revenue/inprs_clm_migration_gate/build_synthetic_file_handoff.py /tmp/inprs-demo
PIN=$(python - <<'PY'
import hashlib
from pathlib import Path
print(hashlib.sha256(Path('/tmp/inprs-demo/source_manifest.json').read_bytes()).hexdigest())
PY
)
python revenue/inprs_clm_migration_gate/file_backed_acceptance.py \
  --manifest /tmp/inprs-demo/source_manifest.json \
  --manifest-sha256 "$PIN" \
  --bundle /tmp/inprs-demo/candidate_bundle.json \
  --root /tmp/inprs-demo
```

For a real engagement, the prime/source-export owner freezes and independently records the manifest SHA **before** candidate acceptance. Do not use the demo builder to mint production authority.

## Paid specialist workshare posture

This is offered only as a **paid specialist subcontract** to a qualified CLM prime. Commercial state is `PROPOSED_NOT_ACCEPTED`; fee, schedule, and prime acceptance remain to be negotiated. No free production delivery is implied.

Proposed deliverables: source-export freeze and manifest receipt; migration byte-reconciliation; document/version-history acceptance; public-portal projection/redaction leakage tests; deterministic exception report and rerun; and an evidence handoff that the prime can attach to its own implementation QA. Prime retains CLM product configuration, INPRS proposal/submission, credentials, legal/compliance conclusions, production access, staffing/references, pricing/signature authority, and final customer acceptance.
