# Open-repo backups

Commons stays writable. Protection comes from recoverable copies, not locks.

`host/repo_backup.py` creates a full `git bundle --all`, an exact ref
inventory, and a SHA-256 manifest; verifies all three; restores into a new
target without overwriting anything; and runs a CI restore drill that writes
an exclusive receipt.

Run snapshots in an ephemeral cloud checkout, then copy both sibling files
(the `.bundle` and `.manifest.json`) to at least one independent cloud
storage provider. A bundle stored only inside the same repository does not
protect against repository deletion.

The measured independent copy is the GitHub Actions artifact uploaded by
`.github/workflows/open-repo-backup.yml` (`commons-open-repo-backup`,
90-day retention). That artifact is independent of git objects and of
Bryce's disk. It is still GitHub-hosted. It is not GitHub-outage protection.
Google Drive and Oracle Always Free are not claimed here.

```sh
python3 host/repo_backup.py snapshot --source . --output-dir /cloud/commons-backups
python3 host/repo_backup.py verify /cloud/commons-backups/commons-*.manifest.json
python3 host/repo_backup.py restore /cloud/commons-backups/commons-*.manifest.json /cloud/restore-check
python3 host/repo_backup.py drill \
  --source . \
  --output-dir "$RUNNER_TEMP/commons-open-repo-backup" \
  --restore-dir "$RUNNER_TEMP/commons-open-repo-restore" \
  --bare \
  --storage github-actions-artifact \
  --retention-days 90 \
  --artifact-name commons-open-repo-backup
```

The restore command refuses an existing target, verifies the bundle before
clone, and reads back restored `HEAD` and every ref name/object ID against
the saved inventory before reporting `RESTORED`. Both bare and work-tree
restores retain local branches, tags, remote-tracking refs, notes, the saved
stash ref, and custom namespaces. Work-tree restores populate only the newly
created target and remove the temporary mirror-push setting; their `origin`
fetch mapping is the ordinary branches-to-remote-tracking mapping.

The v1 manifest records names and object IDs, not symbolic-ref targets.
Reflogs (including older stash entries), repository configuration, the index,
and uncommitted or untracked files are not restored by this bundle format.
No manifest schema change is required for the stronger ref readback.

The drill receipt forces `github_outage_protection: false`,
`same_repo_copy: false`, `owner_disk: false`, and `secrets_present: false`.
No closed branch, peer lockout, or auth layer is added. Do not add GitHub auth,
required reviews, CODEOWNERS, or branch protection. The bundle is a new road;
every existing write road remains open.

Focused real-Git regression checks (including CLI and drill receipts):

```sh
python3 -m unittest -v test_repo_backup test_repo_backup_refs
```

`.github/workflows/lattice-delta-backup-refs.yml` runs these checks on Linux
and Windows for changes to the backup implementation, tests, or contracts.
This focused fixture run is not a claim that the whole live Commons repository
has been restored or that another cloud provider has been provisioned.

The moving-main courier composes with this drill. It does not replace it.
Card: [ground/MOVING_MAIN_MIRROR.md](../ground/MOVING_MAIN_MIRROR.md). Independent
GitLab/Codeberg/object-store copies remain EXTERNAL_PROVIDER_ACTION until a
public origin URL exists.

