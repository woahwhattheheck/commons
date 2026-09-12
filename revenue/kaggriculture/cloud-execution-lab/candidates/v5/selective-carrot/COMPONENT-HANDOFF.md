# TITAN V5 component handoff exporter

`export_staging_component.py` is convergence plumbing for the single production-v3/V5 line. It converts an already-authenticated candidate archive into the exact `titan-v5-staging-component/v1` directory consumed by the landed `staging_composer.py`. It does not decide whether a candidate won a screen or is eligible for CURRENT, release, or Kaggle.

The canonical baseline is fixed by the landed composer to production-v3 SHA256 `20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239`. The candidate archive requires an explicit expected SHA256. When a component is exported against a later composition boundary, `--current`, `--current-sha256`, and `--current-receipt` are a single required authority set. The receipt must be the canonical `titan-v5-single-staging-composer/v1` receipt for those exact current archive bytes: its candidate SHA, member count, and complete member hash map must match before the exporter accepts any prior-writer claim.

The authenticated current receipt is replayed only for composition ownership: ordered component replacement/addition entries reconstruct the exact last writer for each current member. That closes the byte-equality ambiguity where an earlier component legally wrote a postimage identical to the production-v3 baseline. A replacement of any member with a prior composer writer must name that exact writer with `--overlap-after MEMBER=COMPONENT`; an overlap declaration for a current member with no prior composer writer is refused. Deletions are refused. Exact candidate-vs-current byte differences become replacements; candidate-only members become additions. `depends_on` and `conflicts_with` must also be disjoint, so the exporter will not emit a component the composer can never apply.

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
  --current-receipt /path/to/staged-through-p01-receipt.json \
  --candidate /path/to/staged-plus-p05.tar.gz \
  --candidate-sha256 <exact-candidate-sha256> \
  --component-id p05 \
  --depends-on p01 \
  --overlap-after r04_full_router.py=p01 \
  --out-dir /fresh/p05-component
```

The output contains only `COMPONENT.json` plus deterministic SHA-named source payloads under `files/`. Source payloads are the exact changed member bytes from the authenticated candidate archive. Publication is create-exclusive and uses the canonical cooperative fail-closed custody helper; pre-existing final files are never overwritten by the exporter. If a failed publication created output-directory scaffolding during this invocation, rollback removes only directories whose device/inode identities still match this invocation and only while they remain empty. Pre-existing directories, foreign replacements, and nonempty directories are preserved, keeping retries clean without widening deletion authority.

Safety boundaries: archive members are parsed with the landed composer’s exact canonical-file contract, so symlinks/devices/traversal/duplicates reject; deletions and unchanged candidates reject; prior-component replacements require receipt-authenticated exact overlap custody. The exporter never infers dependencies, conflicts, economics, winner status, activation, or release eligibility.