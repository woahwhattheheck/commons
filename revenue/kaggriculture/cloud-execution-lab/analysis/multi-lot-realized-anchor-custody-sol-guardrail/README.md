# TITAN V3 multi-lot realized-anchor custody

This is a structural repair/evidence carrier for rejected multi-lot head
`74a77b154af1783a1c3767e484ff3d801966b73e`. It does **not** revive or promote
that policy.

## Hard predecessor failure

The predecessor counts suffix slots among optimizer candidates only. The bound
scheduler renderer later appends every positive baseline target in
`sorted(targets)` order. Baseline claimants that were not candidates can consume
the supposedly allocated rows.

Minimal witness with two free suffix rows:

- inherited rows: 8 of 10;
- baseline current: `EGG=1`, `MILK=0`, `WOOL=0`;
- scalar anchor: `WOOL=1`;
- extra: `MILK=1`.

The predecessor selects both candidate plans and reports both rows allocated.
The actual renderer emits `EGG, MILK`, dropping the scalar `WOOL` anchor. Scalar
control emits `EGG, WOOL`.

## Repair theorem

The repair computes the scalar control over the **full** baseline current map,
replays the exact sorted-target suffix renderer, including its `available`
shed-capacity clipping, and admits each ranked extra only when every scalar
suffix row remains at the same relative index with a nondecreased quantity and
the scalar anchor remains fully realized. It fails closed when the scalar anchor
itself cannot be realized.

This closes only returned-action anchor custody. It does not prove economic
compositionality, future capacity, market response, or score improvement. Those
remain separate gameplay gates.

## Source binding and disposition

The predecessor module is bound by Git blob
`b7478242f19ef8554bb4e5b102fe1f9b61811a26` and SHA-256
`87e9e14981a4c9ecf6b98bd1eb0b76d5599ff41a2c80bf320e84b3b90d503d89`.
The hosted rejected panel remains authoritative for strength: this carrier makes
no score, merge, enablement, or submission claim.
