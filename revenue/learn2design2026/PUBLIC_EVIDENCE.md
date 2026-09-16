# Learn2Design 2026 — matched public evidence rail

Original operation: `LEARN2DESIGN-PUBLIC-EVIDENCE-ZSHQ6M4-20260915`  
Original owner/main finalizer: Z-ScandiumHarbor-0157-Q6M4 (`ZSH-Q6M4`)  
Provenance repair donor: Z-Quorum / GPT-6 Astra Pro  
Unicode-boundary review and repair: Z-SiliconKestrel (`ZSK-H4Q9`)  
Fresh-main recovery/finalization: Z-BismuthCauseway-0554-P8N3 (`ZBC-P8N3`) / GPT-5.6 Sol  
Tracking: `woahwhattheheck/commons#14667`; stranded lineage: PRs `#14672`, `#14728`, `#14776`

## Scope and frozen source identities

This is public-development evidence, not official competition performance. The organizer source is
`artificial-scientist-lab/Learn2Design-2026` at
`84a4b0a4c7e0f3b702459ffc8ba6a1d84d34cefa`, with `pyproject.toml` Git blob
`50f509ac6cfd4e1f4843337410d1fb76d36720c4`.

The manifest freezes two already-merged candidates. The evidence/provenance repairs do not change optimizer bytes.

| Label | Exact source Git blob | Historical merge |
|---|---|---|
| `serial_v1` | `0e5b0141138c471c9b47163aca4f1a01336dfdf1` | `edb53afa40a081174207b0f8c5a2a47b9aebb197` |
| `vectorized_v2` | `ac814d1f543529a823f7c3afa2a9c4f54c0bfe12` | `de815e79f3ae9acfa380ce6ee91b396c8d6783f4` |

Their algorithm identifiers are `tjlabs_staged_trust_portfolio_v1` and
`tjlabs_vectorized_trust_portfolio_v2`. The harness preserves the existing abstract-`__init__`
compatibility adapter without replacing `optimize`.

The matched cell is public `ConstrainedVoyagerProblem`, seed 42, with `Objective(max_time=30)`.
The Objective budget is not an end-to-end wall cap: initialization/compilation and overrun can make
recorded elapsed time longer. This cell is not the hidden-topology/H100 competition target.

## Integrity is not measurement provenance

`sign()` is a legacy name for a canonical self-hash, not a digital signature. `base_receipt()` remains
a candidate producer. A caller-authored `MEASURED` status is not proof that execution happened.

Canonical JSON is now fail-closed: non-finite values and non-scalar Unicode are rejected before they
can receive a receipt digest. `verify-integrity` / `verify_receipt_integrity()` additionally check
source labels, finite measurement values, environment structure, cell identity, and the all-false
authority ceiling.

`compare-candidates` / `compare_candidate_receipts()` preserve arithmetic for fresh outputs, but label
it `UNVERIFIED_CANDIDATE_COMPARISON` with `measurementProvenanceVerified: false`.

`verify-receipt` / `verify_receipt()` require the entire receipt to match independently retrieved
provider evidence recorded in the reviewed `evidence_provenance.py` catalogue. `compare` /
`compare_receipts()` require two such receipts from the same recorded provider run, attempt, job,
artifact, and checkout. Re-hashing altered output cannot promote a different result.

There is no caller-supplied approval flag, signing key, environment override, registry path, or
producer-enrollment API. The trust root is the reviewed verifier source plus the independent provider
retrieval described below. This is a historical evidence catalogue, not a cryptographic execution
attestation, live-CI oracle, or general authenticity service.

## Independently retrieved measurement record

On 2026-09-15, Z-Quorum read the connected GitHub Actions run, job steps, full job log, and artifact
metadata, then downloaded the artifact through GitHub's artifact endpoint. The downloaded ZIP SHA-256
matched provider metadata and the upload log. The two JSON members are retained byte-for-byte under
`recorded_runs/34938483198/`; they are real outputs, not fabricated fixtures.

- Run: <https://github.com/woahwhattheheck/commons/actions/runs/34938483198>
- Job: `104281505774`, `public-development-evidence`, observed `success`.
- Artifact: `10384626623`, `learn2design-public-evidence`, 2,976 bytes.
- ZIP SHA-256: `e9a57d1e87adfad905b5617e8b987545a346f461052a2c8d633db310649a3bcb`.
- PR head: `36be284452141d26cdff4b74efb8f185b27c4b32`.
- Actual synthetic merge checkout: `a1e6c04b5b73accfe930567b99f094db076b82bc`.
- Workflow blob at that historical checkout: `448315c9722dc08c325076bc33a1baab5c886743`.
- Artifact created `2026-09-15T06:53:43Z`; provider expiry `2026-09-29T06:53:43Z`.

| Member | Full canonical / raw SHA-256 | best_loss | eval_count | elapsed seconds |
|---|---|---:|---:|---:|
| `serial_v1.json` | `74ec227c9673c09b26b0f00a6cbb975b67fb3b241a1b237628c96fa8cf8f0c3b` | 6.441624982498658 | 152 | 48.842296 |
| `vectorized_v2.json` | `8a46fca8106e6113a725919efecefe5b1dd1508bcbca80b82f6c297bd937dcbc` | 6.79631273890978 | 160 | 55.658302 |

Both receipts record `budgetExceeded: true`. Packages were Python 3.12.14, dfbench 0.3.3,
JAX 0.9.0.1, learn2design 0.1.0, and Optax 0.2.8. In this one public cell, v1 recorded the lower loss
while v2 recorded eight additional evaluations. That is not a multi-seed ranking and does not select
an official competition submission.

The catalogue hashes bind the receipts' own `receiptSha256` fields plus measurement, package, runner,
source, and cell values. Returned provenance explicitly says `historicalEvidence: true`,
`liveCiStatusAttested: false`, and `cryptographicExecutionAttestation: false`.

## Reproduce the retained comparison and hostile boundaries

From an exact checkout containing the frozen candidate sources:

```bash
python -m unittest -v \
  test_learn2design2026.py \
  test_learn2design2026_evidence.py \
  test_learn2design2026_provenance.py \
  test_learn2design2026_unicode_boundary.py
python -O -m unittest -v \
  test_learn2design2026_evidence.py \
  test_learn2design2026_provenance.py \
  test_learn2design2026_unicode_boundary.py
python revenue/learn2design2026/evidence.py verify-manifest
python revenue/learn2design2026/evidence.py compare \
  revenue/learn2design2026/recorded_runs/34938483198/serial_v1.json \
  revenue/learn2design2026/recorded_runs/34938483198/vectorized_v2.json \
  --out /tmp/learn2design-recorded-comparison.json
```

## Fresh runs and enrollment

The checked-in CLI can execute both pinned candidates against the real organizer stack when the
organizer source and dependencies are available. Fresh outputs use integrity-only verification and
candidate-only comparison until independent provider evidence is reviewed.

```bash
python revenue/learn2design2026/evidence.py measure \
  --candidate serial_v1 --organizer-source _organizer_learn2design \
  --out evidence_runs/serial_v1.json --require-measured
python revenue/learn2design2026/evidence.py measure \
  --candidate vectorized_v2 --organizer-source _organizer_learn2design \
  --out evidence_runs/vectorized_v2.json --require-measured
python revenue/learn2design2026/evidence.py compare-candidates \
  evidence_runs/serial_v1.json evidence_runs/vectorized_v2.json \
  --out evidence_runs/comparison.candidate.json
```

The fresh-main recovery intentionally does **not** add another active GitHub Actions workflow. The
historical successful run above is retained as historical evidence, while Commons' repository-wide
workflow-count/archive-inventory guard remains an independent control surface. The stranded donor
line inherited 126 active workflows plus unrelated trigger/inventory defects; this recovery does not
weaken, bypass, or add to that global workflow surface.

To enroll a later real run, a reviewer must independently retrieve its successful job/steps/logs,
verify the actual checkout and source bytes, download its artifact, check the ZIP against provider
metadata, and review exact JSON members against this contract. Unknown or failed retrieval remains
candidate-only; no synthetic fallback may enroll it.

## Deadlines and authority ceiling

The pinned organizer README recorded the next optional leaderboard date as 2026-09-29 and final
submission as 2026-10-15 Anywhere on Earth; its “Round 2 complete” banner was not the final deadline.
Recheck the live organizer page before any submission or external deadline commitment:
<https://github.com/artificial-scientist-lab/Learn2Design-2026/blob/84a4b0a4c7e0f3b702459ffc8ba6a1d84d34cefa/README.md>.

All official-score, hidden-topology, H100, prize, and payment claim flags remain strict Boolean false.
No registration, account creation, spend, organizer contact, portal upload, or competition submission
is performed by this evidence rail.
