# BACK UP THE OPEN REPO; DO NOT LOCK IT

Owner law, 2026-08-28. Slack source: `1787927952.994499`.

Commons is unprotected by design. Do not answer that fact with a closed branch
or fewer peer write roads.
Protect the work by making independently verifiable, restorable copies while
leaving every direct posting and push road open.

The executable v1 is [host/repo_backup.py](../host/repo_backup.py).
The scheduled restore drill is
[.github/workflows/open-repo-backup.yml](../.github/workflows/open-repo-backup.yml).

A valid backup contains:

1. a full `git bundle --all` of the actual repository;
2. a machine-readable inventory of every bundled ref;
3. the source `HEAD`;
4. SHA-256 of the bundle;
5. a schema-versioned manifest;
6. a restore readback proving restored `HEAD` equals the manifest.

A same-repository copy is useful against accidental branch movement but not
repository deletion. Copy the bundle and its manifest to independent cloud
storage. Never create new Commons clones, bundles, or archives on Bryce's
space-constrained local machine; use ephemeral cloud execution and durable
cloud storage.

The measured v1 independent copy is a GitHub Actions artifact with 90-day
retention. It is independent of the git object store and of Bryce's disk. It
is still GitHub-hosted. It is not GitHub-outage protection and not
account-deletion protection. Do not mint a live Drive, Oracle, S3, or GCS
receipt without a real provider receipt.

No overwrite is part of restore. Restore into a new absent path, verify, then
choose the recovery action from evidence.

The same-account GitHub copy [`woahwhattheheck/commons-backup`](https://github.com/woahwhattheheck/commons-backup)
is a 5-minute live-mirror of canonical `main` onto backup `main` (workflow on
backup `ops`: `.github/workflows/mirror.yml`). Actions `GITHUB_TOKEN` cannot
create or update `.github/workflows` files. The executable is
[host/live_mirror.py](../host/live_mirror.py): exact-push when GitHub allows it,
otherwise preserve dest workflow blobs so the rest of the corpus still moves.
Dest `main` is force-updated: a grafted backup commit is not an ancestor of the
next source SHA. Source SHA is recorded at `refs/backup/source-main`. Missing GitHub App
`workflows` permission is not a Commons lock and not a reason to add a PAT.

Do not add GitHub auth, required reviews, CODEOWNERS, or branch protection.

The moving-main courier composes with this drill and does not remint it:
[host/moving_main_mirror.py](../host/moving_main_mirror.py),
[MOVING_MAIN_MIRROR.md](./MOVING_MAIN_MIRROR.md). ntfy cursor and Software
Heritage Save Code Now are the zero-new-credential automatic roads. GitLab,
Codeberg, and object-store full-bundle copies stay EXTERNAL_PROVIDER_ACTION
until a public origin URL exists.

