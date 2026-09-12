# TITAN V5 component handoff exporter

`export_staging_component.py` is convergence plumbing for the single production-v3/V5 line. It converts an already-authenticated candidate archive into the exact `titan-v5-staging-component/v1` directory consumed by the landed `staging_composer.py`. It does not decide whether a candidate won a screen or is eligible for CURRENT, release, or Kaggle.

The canonical baseline is fixed by the landed composer to production-v3 SHA256 `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`. The candidate archive requires an explicit expected SHA256. When a component is exported against a later composition boundary, `--current` also requires its explicit SHA256. Deletions are refused. Exact byte differences become replacements; candidate-only members become additions. A replacement whose current preimage already differs from production-v3 must name the prior owner with `--overlap-after MEMBER=COMPONENT`; an overlap declaration on a baseline-owned member is refused.

Before publication, the exporter writes the generated manifest and payloads to private temporary storage and requires the **landed composer itself** to accept them through `staging_composer.load_component()`. There is no parallel schema implementation or second component format. Final `COMPONENT.json` plus source payloads are then published through the shared `publication_custody.publish_exclusive` primitive.

Direct production-v3 delta:

```bash
python -B export_staging_component.py \
  --baseline /path/to/production-v3.tar.gz \
  --candidate /path/to/measured-winner.tar.gz \
  --candidate-sha256 <exact-winner-sha256> \
  --component-id p05-measured-winner \
  --out-dir /fresh/p05-component
```

Reviewed component that replaces bytes already written by `p01`:

```bash
python -B export_staging_component.py \
  --baseline /path/to/production-v3.tar.gz \
  --current /path/to/staged-through-p01.tar.gz \
  --current-sha256 <exact-current-sha256> \
  --candidate /path/to/staged-plus-p05.tar.gz \
  --candidate-sha256 <exact-candidate-sha256> \
  --component-id p05 \
  --depends-on p01 \
  --overlap-after r04_full_router.py=p01 \
  --out-dir /fresh/p05-component
```

The output contains only `COMPONENT.json` plus deterministic SHA-named source payloads under `files/`. Source payloads are the exact changed member bytes from the authenticated candidate archive. Publication is create-exclusive and uses the canonical cooperative fail-closed custody helper; pre-existing final files are never overwritten by the exporter.

Safety boundaries: archive members are parsed with the landed composer’s exact canonical-file contract, so symlinks/devices/traversal/duplicates reject; deletions and unchanged candidates reject; prior-component replacements require explicit overlap custody. The exporter never infers dependencies, conflicts, economics, winner status, activation, or release eligibility.