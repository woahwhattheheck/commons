# Backup HEAD identity

`host/repo_backup.py` writes `commons-open-repo-backup/v2` manifests.
The new `head_ref` field is the symbolic HEAD target (for example,
`refs/heads/feature`), or JSON `null` for a detached HEAD. The bundle,
all-ref inventory, SHA-256, and source HEAD commit remain in the manifest.

Git bundles advertise the HEAD commit but do not retain whether HEAD was
attached to a particular branch. With `main` and `feature` at the same commit,
a mirror clone can select `main` even when the source had `feature` checked
out. Comparing only the commit and `show-ref --head` inventory does not detect
that difference. Likewise, a detached source at a branch tip can become attached.

The v2 reader checks the recorded symbolic target against the bundled refs and
HEAD commit. Restore explicitly sets the recorded attached or detached state,
reads it back, and then performs the existing commit and complete-ref checks.
This applies to both bare and working-tree restore targets. A changed source
HEAD detected during snapshot prevents publication of that snapshot manifest.
This is a boundary check, not an atomic snapshot of a concurrently mutating Git
repository.

## Compatibility

The current reader still accepts v1 manifests and retains their previous restore
behavior and receipt shape. V1 did not record branch attachment, so a legacy
manifest cannot recover that information. Historical v1-only tool versions do
not understand v2 manifests; use the updated tool when restoring new snapshots.
Existing bundles and manifests are not rewritten.

The drill receipt remains `commons-open-repo-backup-drill/v1`; its field set,
storage description and retention remain unchanged. Existing restore targets
remain untouched. A GitHub-hosted backup is not GitHub-outage protection.

## Validation

Operation: `mica-backup-head-identity-20260908-01`.
Original production blob: `21d81d970cdbc51fb5eedffb81f882903838a643`.
Original existing test blob: `da73f4f4b79d5af6346a79992ee973529f663de3`.

The real Git baseline reproduced source HEAD `refs/heads/feature` restoring as
`refs/heads/main` while both commit equality and full ref-inventory equality
passed. The added suite against original production ran 12 methods with 8
failures and 1 error; this includes new-schema expectations as well as the
attached/detached regressions. Against the repair, all 12 methods passed in
3.387 seconds:

```sh
python -B -m unittest test_repo_backup_head_identity -v
```

Eight unchanged runtime methods from `test_repo_backup.py` also passed in
4.963 seconds. In the scoped cloud checkout these were selected from the exact
original test AST, excluding the unrelated guard import and three documentation
or guard-only methods. Test assertions and production functions were unchanged
by that selection. Coverage includes snapshot/verify/restore, complete refs,
bundle tampering, existing-target preservation, CLI operations, and drill
receipt flags. The full repository suite and those three excluded methods were
not run for this change. Python compilation passed.

Only the existing `snapshot`, `read_manifest`, `verify`, and `restore` function
bodies changed, alongside the new `_head_ref` helper and schema constants.
The existing drill, CLI, hashing, exclusive-write and ref-enumeration function
ASTs remain unchanged. Tests use temporary Git repositories in the provided
cloud environment; no owner-device work, new cloud infrastructure, provider
operation, or TITAN simulation is part of this repair.
