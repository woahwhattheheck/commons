# Biohub Cell Tracking — data-free submission readiness

This lane is a **public-contract scaffold**, not a Kaggle submission and not a trained competition model. It lets a peer exercise the highest-risk plumbing—node/edge CSV construction, lineage invariants, physical-coordinate linking, deterministic packaging, and offline validation—without putting any competition bytes into Commons or a hosted model.

## Public contract pinned on 2026-09-08

- Competition: `Biohub - Cell Tracking During Development` — $60,000 prize pool.
- Entry/team merger deadline: 2026-09-22 23:59 UTC. Final submission deadline: 2026-09-29 23:59 UTC.
- Scoring runs as a Kaggle Notebook with internet disabled and a CPU or GPU runtime limit of 12 hours.
- `submission.csv` has exactly ten columns: `id,dataset,row_type,node_id,t,z,y,x,source_id,target_id`.
- Node rows contain dataset-scoped node IDs plus integer `(t,z,y,x)` voxel centroids and use `-1` edge sentinels.
- Edge rows contain dataset-scoped `(source_id,target_id)` references and use `-1` node/coordinate sentinels.
- The organizer scorer keeps only consecutive tracking edges (`t→t+1`) for edge accounting.
- Dataset names match test folder names without `.zarr`; every hidden-test dataset must appear.
- Public data description: Zarr v3 image volumes `(T,Z,Y,X)`; physical voxel scale `(z,y,x)=(1.625,0.40625,0.40625)` microns/voxel; sparse GEFF ground truth for training only.

Authoritative references and the exact organizer starter commit are recorded in `SOURCE_LOCK.json`. `OFFLINE_RUNTIME.md` records the public starter dependency/runtime hazards that matter when moving from this standard-library smoke path into a real Kaggle notebook.

## Run the zero-data smoke path

```bash
cd research/biohub-cell-tracking-readiness
python synthetic_baseline.py --output /tmp/submission.synthetic.csv
python submission_contract.py /tmp/submission.synthetic.csv --strict-lineage
python -m unittest discover -s tests -v
```

The synthetic baseline creates two moving 3D tracks across four timepoints, links them one-to-one in **physical microns** rather than raw voxel distance, writes the public CSV schema, round-trips it byte-for-byte, and validates `rows=14`, `nodes=8`, `edges=6`, and `divisions=0`. It is intentionally tiny and deterministic and does **not** infer divisions from leftover nearby detections.

Positive division coverage lives in an isolated contract fixture: one parent at `t=0` links to exactly two known children at `t=1`, then the writer→reader→validator→rewrite path proves `rows=5`, `nodes=3`, `edges=2`, `divisions=1`, consecutive IDs, and byte-identical output without broadening the baseline tracker.

## Use on a real local prediction

Do not copy challenge data into Commons. On the machine that is already authorized to hold the competition data:

1. Convert model detections to integer voxel centroids `(t,z,y,x)` and assign dataset-scoped node IDs.
2. Convert temporal links to `(source_id,target_id)` edge rows.
3. Write `submission.csv` with `write_submission()` or another deterministic writer.
4. Create a private newline-delimited file containing all test dataset names.
5. Run:

```bash
python submission_contract.py submission.csv --expected-datasets private_test_names.txt --strict-lineage
```

Consecutive `t→t+1` tracking edges are enforced by default. `--strict-consecutive` remains a compatibility spelling. The Python API permits `require_consecutive_edges=False` only for deliberate non-submission analysis.

The Commons readiness policy is also conservative by default: `strict_lineage=True` / `--strict-lineage` rejects exact duplicate edges, multiple parents, and more than two children. Those three guards are **local lineage-readiness policy, not universal organizer CSV-invalidity**. The pinned organizer path can ingest these broader graph shapes; its edge-scoring path deduplicates exact source→target pairs and caps outgoing edges for edge accounting, while division scoring evaluates graph topology separately. Use `--organizer-compatible` (or `strict_lineage=False`) only for local exploration of that broader organizer-ingestible graph surface. Its compact lineage counts are a readiness summary, not a full scorer emulation; headers, IDs, sentinels, references, forward time, and default `t→t+1` remain strict.

## What this validator catches universally

- wrong header or non-consecutive throwaway `id` values;
- leading/trailing whitespace in literal `dataset` or `row_type` tokens;
- `.zarr` suffix leakage in dataset names;
- malformed node/edge sentinel fields;
- duplicate node IDs inside a dataset;
- missing edge endpoints;
- non-consecutive, backward, or self links;
- missing or unexpected datasets when a private expected-set list is supplied.

With the default strict-lineage policy it additionally rejects exact duplicate edges, multiple parents, and sources with more than two children. These stricter topology guards are intentionally labeled separately from organizer ingestion and metric-specific edge handling.

## Deliberate exclusions

No competition images, GEFF labels, hidden-test names, derived features, trained weights, Kaggle credentials, leaderboard scores, ranks, entry acceptance, submission receipt, award, or payment are contained or claimed here. This scaffold does not replace the organizer's scorer or a competitive detector/tracker.
