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

1. a full `git bundle --single-worktree --all` of the actual repository;
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

`verify <manifest>` checks the bundle checksum and ref inventory, then restores
it into a temporary bare repository and checks the resulting HEAD and refs.
Only that successful readback returns `VERIFIED`; matching hashes and headers
alone cannot prove that all required commit parents and objects are present.
The temporary repository is removed on success or failure. Run verification in
cloud scratch space with room for an unpacked repository. `restore` performs
the same checks in its requested destination without an extra temporary copy.

`snapshot --source` and `drill --source` accept both Git work trees and bare
repositories. A mirror or a recovery created with `restore --bare` can be backed
up directly, without allocating a work tree. The same bundle ref inventory,
symbolic or detached HEAD, and restore readback checks apply to either source.

The source must have complete history. Shallow clones are rejected before any
bundle or manifest is written: Git can create a bundle whose refs and checksum
look valid while leaving out parents required to restore it. Run
`git fetch --unshallow` in the source (or use a full clone) and retry. For a
GitHub Actions checkout, set `fetch-depth: 0`, as the scheduled drill already
does. Sparse work trees and partial clones are permitted when their history is
complete; Git may download missing objects while building their bundle.

For repositories with linked work trees, the snapshot contains every shared
ref (including each work tree's named branch) and the chosen source's HEAD.
It excludes other work trees' private pseudo-refs, which are not ordinary
repository refs and cannot be restored by a mirror clone. Back up each detached
work tree separately if its HEAD is not retained by a shared branch or tag.
Work tree directories, index state, and uncommitted files are outside this
Git-object backup.

```bash
python3 host/repo_backup.py snapshot --source /cloud/recovered.git --output-dir /cloud/next-backup
python3 host/repo_backup.py restore /cloud/next-backup/commons-<stamp>-<sha>.manifest.json /cloud/next-recovery.git --bare
```

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

## Live cash

Verified product pages only — no invented Stripe links.
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../commercial.html). Not remints of tip SKUs.

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260905-03 — do not remint.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.
