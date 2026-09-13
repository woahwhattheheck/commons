# Cross-network custody & temperature evidence gate

This is an **offline, read-only evidence-completeness core** for the `life-couriers-global-custody-temperature-evidence-gate-01` delivery lane. It joins declared shipment and leg evidence across custody, timestamps, lane/time windows, packout↔sensor lineage, declared document validity, excursion/window incidents, recipient identity and proof of delivery. Each leg is projected as `EVIDENCE_COMPLETE` or `HOLD` with stable reason codes; shipment state is the conservative aggregation of its legs.

The core does **not** dispatch a route, classify clinical material, identify a patient, decide temperature disposition, make a customs judgment, release a shipment, or mutate a carrier/client/provider system. Those decisions stay with named operations/quality staff. Secret-shaped fields, direct patient identifiers and authority-shaped decision fields are rejected before evaluation.

## Signature boundary

`prepare_manifest()` evaluates evidence and emits a canonical SHA-256 `manifest_digest`. `sign_manifest()` accepts a caller-injected detached signer that receives only the 32-byte digest; the core never loads or stores a private key. `attach_signature()` can attach a buyer-controlled detached signature produced out of process after revalidating the manifest digest. Production deployments should use the buyer's KMS/HSM/Ed25519-equivalent signer and verifier policy.

`fixture.py` contains an explicitly **synthetic-only** deterministic HMAC signer so the frozen acceptance run can prove three byte-identical signed manifests without embedding or pretending to provide a production credential. That fixture key is public test data and must never be treated as production signing material.

## Frozen acceptance

`python3 revenue/life_couriers_custody_evidence_gate/cli.py acceptance`

The generator creates exactly 240 synthetic time-critical shipments across six declared service lines, three legs each. Expected result: 192 `EVIDENCE_COMPLETE`, 48 `HOLD`, with exactly eight shipments in each demanded defect family: custody gap, packout/temperature mismatch, expired document, unacknowledged time-window breach, duplicate/orphan leg graph, and incomplete recipient/POD. Every valid shipment must complete; every defective shipment must hold with its exact single expected code; three full signed reruns must be byte-identical.

## Generic use

1. `cli.py prepare shipments.json > prepared.json`
2. Sign the printed `manifest_digest` with buyer-controlled signing infrastructure.
3. `cli.py attach prepared.json --signer-id ... --algorithm ... --signature ... > signed.json`

Attaching a string records the external signature envelope; cryptographic verification policy remains outside this repo because the buyer owns the signer/trust root. The manifest itself states `dispatch_authorized=false`, `release_authorized=false`, and does not infer clinical, temperature-disposition, or customs decisions.
