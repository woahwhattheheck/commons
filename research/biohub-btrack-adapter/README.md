# Biohub BTrack adapter

Data-free integration scaffold for the Biohub Cell Tracking During Development paid competition lane. It converts explicit `(dataset,detection_id,t,z,y,x)` point detections into a **pinned BTrack v0.7.0** run and then into Commons submission node/edge rows. This directory contains no competition data, model weights, Kaggle credentials, score, rank, award, or payment claim.

## Reproducibility boundary

Upstream is pinned to `quantumjot/btrack` **v0.7.0**, source commit `a3bd947915efe6837936f9db6db88417f0b51b45` (MIT). Real execution requires that exact package/runtime and an audited BTrack configuration. The pure adapter tests inject a fake tracker; they do **not** claim a native BTrack/GLPK run. The offline dependency lane must separately prove the v0.7.0 wheel/native library and `cvxopt.glpk.ilp` work in the target notebook image before optimizer-backed lineage is called ready.

## Safety/identity rules implemented here

* Detections are sorted deterministically before `append()`. BTrack v0.7.0 overwrites incoming localization IDs with `0..N-1`; the adapter freezes that sequential ref -> original integer voxel detection map and also tags each object with `commons_detection_id`.
* Output coordinates always come from the immutable original detection map, never from BTrack's physical `x/y/z` values.
* The adapter converts `tracker.tracks` **immediately** after tracking/optimisation and never invokes list-mode HDF export first. BTrack v0.7.0 `HDF5FileHandler.write_tracks(list[Tracklet])` mutates object IDs before recomputing `Tracklet.refs`; the independent property tag + coordinate/time checks fail closed if ref identity changed.
* Each Commons `dataset` gets a fresh `BayesianTracker`, fresh ref map, fresh volume and output accumulator. Multiple dataset values are never appended into one native engine.
* Voxel `(z,y,x)` positions are scaled into physical BTrack `(x,y,z)`. Configured volume is reordered/scaled into the same units and `max_search_radius` is explicitly a physical distance. `optimise=True` additionally requires an explicit `optimizer_distance_units="physical"` attestation for the external BTrack configuration.
* Dummy/negative refs never become Commons nodes or edges. A track that would bridge nonconsecutive real observations fails closed; emitted edges are strictly `t -> t+1`.
* Parent/child Tracklet lineage is converted as parent-last-real -> child-first-real. The adapter rejects unknown refs/tracks, duplicate track IDs, >1 parent, >2 children, and non-adjacent lineage.

The default scale is the currently routed Biohub anisotropy pin: `z=1.625`, `y=x=0.40625` physical units per voxel. Volume bounds remain explicit inputs rather than being inferred from detections because BTrack uses the configured imaging volume in border/hypothesis logic.

## CLI shape

```text
python adapter.py \
  --detections detections.csv \
  --output submission.csv \
  --config audited_cell_config.json \
  --max-search-radius 8.5 \
  --zlo 0 --zhi <z-max> --ylo 0 --yhi <y-max> --xlo 0 --xhi <x-max>
```

Add `--optimise --optimizer-distance-units physical` only after the configuration's optimizer thresholds have been audited into the same physical coordinate system and the offline GLPK smoke has passed.

## Data-free acceptance

`test_adapter.py` covers deterministic sorting/CSV bytes, anisotropic physical-coordinate equivalence, physical volume/radius propagation, one-engine-per-dataset isolation, exact two-child lineage conversion, dummy/gap rejection, unknown refs, the HDF-style valid-ref permutation guard, optimizer-unit fail-closed behavior, and original voxel-coordinate preservation.
