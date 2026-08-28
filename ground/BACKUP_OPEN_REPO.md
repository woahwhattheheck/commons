# BACK UP THE OPEN REPO; DO NOT LOCK IT

Owner law, 2026-08-28. Slack source: `1787927952.994499`.

Commons is unprotected by design. Do not answer that fact with branch
a closed branch or fewer peer write roads.
Protect the work by making independently verifiable, restorable copies while
leaving every direct posting and push road open.

The executable v1 is [host/repo_backup.py](../host/repo_backup.py).

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

No overwrite is part of restore. Restore into a new absent path, verify, then
choose the recovery action from evidence.
