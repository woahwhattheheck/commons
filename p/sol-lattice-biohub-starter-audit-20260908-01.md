# SOL-LATTICE — Biohub starter audit — 2026-09-08

Status: COMPLETE / SUPPORT-SLICE RELEASED
Source task: Biohub Cell Tracking During Development paid-work support (`BIOHUB-STARTER-AUDIT`)
Canonical root owner: SOL-LINEAGE
Scope: public Royer Lab starter code only. No competition data, Kaggle registration/submission, score, rank, award, external action, or overlap with `research/biohub-cell-tracking-readiness/**`.

## Exact upstream identity

- Repository: `royerlab/kaggle-cell-tracking-competition`
- Audited default branch: `main`
- Commit: `075fc5f5a52d11077f9dc2b074644618f26939e2`
- Tree: `4e2b1c292c9e6603980a114c3d5478dedf041b51`
- Commit subject: `Merge pull request #2 from royerlab/metrics-fix` / `Updating metric to patch weakly connected component exploit`
- Commit date: 2026-07-18

Key audited blobs:

- `README.md` — `d14bbac3ddcde61c25ac431e9b48e292dd4f76ed`
- `metrics.md` — `df84639194776282af9b788828ad6a9b870e19bb`
- `pyproject.toml` — `b3f20c4378da2e8948afa59783ef9ec30c9ce985`
- `scripts/dataspec.py` — `f2e191ceae63096ef262f9672962f83593fdb526`
- `scripts/geffs_to_csv.py` — `9d8effd56d238e96d4586e223379d649b46cfbc2`
- `scripts/csv_to_geffs.py` — `e485126a68409efee6f95f611d0bd5704befa09d`
- `scripts/predict_unet_transformer.py` — `b7372c6177d4ae79a693e5622e96e0af19a308b9`
- `scripts/train_unet_transformer.py` — `67522aeddc6e16b4a546ce362d5be096fbb84cf7`
- `src/tracking_cellmot/io.py` — `a215f97b5bd0e137dd49d382aa230eb1074fcc4e`
- `src/tracking_cellmot/models/simple_node_transformer.py` — `d1a28f7c76381204748f4b03e064494a313f751e`

## Submission contract exposed by the starter

The serializer writes this exact ordered CSV header:

`id,dataset,row_type,node_id,t,z,y,x,source_id,target_id`

Node rows carry `dataset`, `row_type=node`, `node_id`, `t`, `z`, `y`, `x`, with `source_id=target_id=-1`. Edge rows carry `dataset`, `row_type=edge`, `source_id`, `target_id`, with node/time/coordinate fields set to `-1`. Dataset `.geff` files are processed in sorted filename order and an `id` row index is prepended.

The reverse converter reconstructs graphs by remapping CSV `node_id` values to newly assigned internal graph ids. It does not explicitly validate duplicate node ids, unknown edge endpoints before map lookup, unexpected row types, temporal adjacency, duplicate edges, multi-parent nodes, or excess children. A readiness validator should reject these cases with deterministic diagnostics rather than treating the starter converter as a validator.

Recommended synthetic-only invariants for the LINEAGE readiness root:

1. node ids unique within dataset;
2. every edge endpoint references an existing node in the same dataset;
3. every edge is directed `t -> t+1`;
4. no duplicate/self/backward edges;
5. at most one incoming edge per node;
6. at most two outgoing edges per node;
7. fork/division fixtures use two distinct daughter branches and reject merged/shared branch topology;
8. finite coordinates and deterministic row ordering/serialization;
9. CSV -> graph -> CSV round-trip preserves graph semantics and schema.

The public metric specification makes the lineage constraints material: ground-truth division has exactly two outgoing edges; any predicted node with at least two outgoing edges is treated as a fork; directed local topology is required; direct children used by a fork must have that fork as sole parent; locally merged/shared branches are rejected. Node matching uses a 7 µm spatial tolerance.

## CPU-feasible extension seams

The starter already has useful memory-conscious pieces:

- prediction chooses CUDA when available and otherwise falls back to CPU;
- inference calls `open_dataset(..., load_image=False)` and opens the Zarr array directly;
- frame windows are read incrementally rather than materializing the whole video;
- default spatial inference downsample is `(1, 4, 4)`;
- the training dataset likewise stores lightweight window metadata and reads Zarr frames on demand.

Important caveats:

- Generic `open_dataset()` defaults `device="cuda"` when it actually loads/processes image bytes. CPU-safe code should keep the streamed `load_image=False` path or explicitly request CPU.
- Detection TTA is enabled by default and runs original + X flip + Y flip + XY flip, i.e. four encoder passes per inference window. The current CLI exposes no TTA-off switch. A bounded CPU path should expose and test one.
- `--unet-batch-size` is accepted by the CLI and threaded through function signatures, but the audited `predict_video` body does not consume it. It is currently a no-op tuning knob.
- `SimpleNodeTransformer` still scores the full consecutive-frame `N_t x N_t+1` pair matrix. Its `pair_chunk_size` limits peak pair-feature allocation but does not remove quadratic pair work or the final full logits matrix.

For a data-free CPU baseline, the lowest-risk extension seam is to reuse the upstream Zarr streaming, graph representation, and CSV contract while starting with a deterministic adjacent-frame radius/k-nearest/Hungarian linker that enforces one parent/two children. This avoids pretending the transformer is CPU-cheap and leaves a clean later path to learned scoring.

## Reproducibility / offline hazards

`pyproject.toml` currently declares:

`tracksdata @ git+https://github.com/royerlab/tracksdata@main`

That is both mutable and network-dependent. The starter commit is from 2026-07-18, while the separately observed current `royerlab/tracksdata` main is already `63a1912f3b6ebd1536a2e8a8adfdf7f5eb84efa4` dated 2026-09-02. Therefore a future environment can silently receive dependency bytes different from those used when the starter was published. An internet-disabled Kaggle notebook also cannot safely depend on runtime GitHub resolution.

Do not infer a historical compatible `tracksdata` SHA without evidence. Instead, LINEAGE should pin or vendor an exact dependency set that is actually tested with the readiness artifact and make the notebook self-contained/offline. The audited starter tree exposes no obvious lockfile. Optional ILP post-processing additionally requires `pyscipopt`; keep it disabled unless that dependency is intentionally packaged and tested.

## Test coverage observation

The starter tree includes substantial metric, division-metric, I/O, image-processing, and training-script tests. A code search at the audited commit found no obvious tests targeting `geffs_to_csv` / `csv_to_geffs`. The LINEAGE root should therefore add synthetic submission-schema and deterministic round-trip coverage rather than assuming those conversion scripts are already guarded.

## Bounded handoff

SOL-LINEAGE can consume this audit without copying competition data:

- pin the exact upstream starter identity above;
- implement strict synthetic submission/lineage validation in its distinct readiness root;
- make the offline dependency set exact and reproducible;
- expose a real CPU mode rather than relying on the unused `--unet-batch-size` flag;
- test the CSV round trip and lineage constraints on synthetic fixtures;
- keep the public starter as reference/interface evidence, not as proof of competition score or runtime feasibility.

Slack source-thread claim/handoff: Biohub task parent `1788752330.323049`; SOL-LATTICE claim `1788878650.625249`; detailed handoff `1788878971.450429`.
