# Open-repo backups

Commons stays writable. Protection comes from recoverable copies, not locks.

`host/repo_backup.py` creates a full `git bundle --all`, an exact ref
inventory, and a SHA-256 manifest; verifies all three; and restores into a new
target without overwriting anything.

Run snapshots in an ephemeral cloud checkout, then copy both sibling files
(the `.bundle` and `.manifest.json`) to at least one independent cloud
storage provider. A bundle stored only inside the same repository does not
protect against repository deletion.

```sh
python3 host/repo_backup.py snapshot --source . --output-dir /cloud/commons-backups
python3 host/repo_backup.py verify /cloud/commons-backups/commons-*.manifest.json
python3 host/repo_backup.py restore /cloud/commons-backups/commons-*.manifest.json /cloud/restore-check
```

The restore command refuses an existing target, verifies the bundle before
clone, and reads back restored `HEAD` against the manifest. No closed branch, peer lockout, or auth layer is added. The bundle is
a new road; every existing write road remains open.
