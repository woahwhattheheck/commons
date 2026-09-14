# Methods note — geometry moments for zero-shot tokamak transfer

## Objective

Improve the *transfer hypothesis* before spending submission budget. DIII-D and MAST expose the same physical classes of information—actuator currents, plasma current, toroidal field, Thomson profiles and machine geometry—but their coil names, conductor granularity and current units differ. A model that binds identity to `F1A`, `F2A`, … has no natural MAST input vocabulary.

## Representation

For every powered coil input column `c`, interpolate only its finite native samples onto `efit_times`. Let `(r_c,z_c)` be the average of all released conductor rows driven by that column, mapped to `[-1,1]²` in the machine's native EFIT box. The column current is converted to `asinh(I_c / s)` where `s` is the median 95th-percentile magnitude across powered columns in that shot.

We aggregate signed and magnitude-weighted moments over the six basis functions

`[1, r, z, r², z², rz]`.

The result has fixed width regardless of whether the machine has 19 lumped DIII-D coil rectangles or hundreds of MAST conductor elements. Critically, geometry is *averaged inside each powered column first*. Repeated MAST conductor rows therefore refine where a source sits; they do not multiply its current by its element count.

Plasma current and TF are separately normalized by their own input-only per-shot robust scales. Thomson Te/ne profiles use input-only per-shot scale normalization and per-frame distribution summaries, which avoids assuming equal channel counts or identical chord topology.

No statistic is fit across the DIII-D or MAST public-test cohort.

## Target and model

DIII-D flux maps are compressed with deterministic full-SVD PCA. PCA fitting uses at most a fixed number of frames per shot so long discharges cannot dominate the basis. The model standardizes features with `RobustScaler` and averages three multi-output ridge regressors with fixed alphas. `q95` and `betaN` use parallel ridge heads.

This is intentionally a strong transparent baseline rather than a huge neural network. It makes machine-transfer errors inspectable and creates a trustworthy baseline for later nonlinear successors.

## Selection discipline

Every candidate comparison is whole-shot cross-validation. PCA, scaling and regression are refit inside each training fold. The helper's reported `partial_composite = 0.55*R2_psi + 0.15*R2_scalars` omits the organizer-only LCFS/consistency terms and must never be quoted as the challenge score. Real model selection should call the starter's pinned `local_score.py` on held-out training shots.

## Challenge-2 logic

A transfer feature change is useful only if DIII-D remains strong enough to clear the current `S_model >= 0.85` gate. The code's `transfer_retention()` encodes that gate for bookkeeping, but only organizer-scored machine composites can make its numeric output competition-relevant.

## Failure modes explicitly tested

- same shot appearing in both train and validation;
- DIII-D Ip blanket shifting instead of per-shot repair;
- MAST union-clock NaNs treated as signal dropouts;
- MAST Thomson ghost-channel misalignment;
- EFIT targets affecting feature extraction;
- another public-test shot changing this shot's features;
- long shots dominating PCA by frame count;
- malformed/extra submission keys or extra direct-upload ZIP members;
- DIII-D NaN/Inf output;
- nondeterministic NPZ/ZIP bytes;
- post-package file tampering.
