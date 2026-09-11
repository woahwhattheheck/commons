# Artifact registry

`host/artifact_registry.py` implements visibility-plan E1 as a deterministic, offline SHA-256 custody ledger. The SHA-256 key is the measured byte identity; a row then records durable coordinates where those bytes were observed.

Supported source coordinates are Git blobs, Git commits, a path at an exact Git commit, Slack files, and workflow artifacts. A workflow artifact is accepted only when its producing `run_id`, `job_id`, artifact id/name, and **job conclusion** are present. The same durable locator cannot be rebound to a different SHA-256, and the same locator cannot silently change metadata inside one artifact row.

This is a **registry, not a remote-byte verifier**. Adding `{"kind":"git_blob", ...}` says that the producer bound a measured SHA-256 to that Git blob coordinate; it does not claim this module fetched GitHub and recomputed the SHA-256. Use a separate verifier when that proof is required.

The file format is:

```json
{
  "schema": "commons-artifact-registry/v1",
  "artifacts": {
    "<64-char lowercase sha256>": {
      "sha256": "<same sha256>",
      "size_bytes": 123,
      "labels": ["optional-label"],
      "sources": [
        {"kind": "git_blob", "repo": "owner/repo", "blob_sha": "<40-hex>"}
      ]
    }
  }
}
```

The parser rejects duplicate JSON keys and non-finite JSON. Integer identifiers are exact integers, so booleans are not accepted as workflow ids. Writes are deterministic and atomic on the local filesystem.

Examples:

```bash
python host/artifact_registry.py hash package.tar.gz
python host/artifact_registry.py add artifacts.json "$SHA256" \
  --size-bytes "$BYTES" \
  --source-json '{"kind":"path","repo":"owner/repo","commit_sha":"<40-hex>","path":"dist/package.tar.gz"}'
python host/artifact_registry.py validate artifacts.json
python host/artifact_registry.py get artifacts.json "$SHA256"
```

A workflow artifact receipt should use `kind=workflow_artifact` and record the producing job conclusion rather than inferring success from artifact existence.
