# Exact Git source capsules in Commons context packets

`host/context_dispatch.py` can attach bounded source text to an existing
`commons-context-packet/v1` without reading the working tree.

This is a handoff aid, not repository authority. It packages explicitly requested
public/local Git blobs from one exact commit so another worker can receive the
relevant source together with ownership, coordination, event, and resource context.

## Source authority

A source request is valid only when all of these are supplied together:

- `--source-commit`: an exact lowercase 40-hex commit object;
- one or more `--source-path`: canonical repository-relative paths;
- `--git-repo`: the local Git repository whose object database is authoritative
  (defaults to the Commons root).

The implementation does **not** open those paths in the working tree. It resolves
the exact commit tree with Git object commands, requires each requested path to
resolve to exactly one ordinary `100644` or `100755` blob, obtains the exact blob
size, and hashes blob bytes streamed from `git cat-file`.

Symlinks, gitlinks/submodules, trees, missing paths, ambiguous pathspecs, traversal,
absolute paths, backslashes, control characters, noncommit object IDs, and malformed
Git results fail closed.

## Capsule identity

Every requested path produces source identity metadata:

- exact source commit and commit-tree SHA;
- repository-relative path;
- Git mode;
- Git blob SHA;
- SHA-256 of the exact blob bytes;
- exact byte count.

Text is included only when the blob is within `--max-source-file-bytes` and strict
UTF-8 without binary control characters. Oversize, non-UTF-8, or binary/control
content is **not truncated and mislabeled as source**: the packet retains exact
identity metadata and an explicit omission reason.

The packet's ordinary `--max-chars` bound still wins. If a valid text blob would
overflow the whole packet, its complete text is omitted rather than truncated.
`omitted.git_source_text_files` and `omitted.git_source_text_bytes` report the
omission. Ownership and active coordination rows are budgeted before source text;
source text is budgeted before recent/resource context.

## Moving main

`git_source.commit` is always the exact caller-selected source commit.
`git_source.observed_main_head` and
`git_source.source_commit_matches_observed_main` are drift metadata captured from
the local `refs/heads/main` at packet compilation time. A later main advance never
relabels the capsule or changes its committed source identity.

Packet verification checks the semantic SHA-256 and packet budget. The CLI's
`verify` and `render` commands additionally re-read the exact commit and requested
blobs from `--git-repo`; content identity, blob identity, mode, byte count, and any
included text must still match. Drift of the current `main` ref is deliberately
not treated as source drift.

## Example handoff

```bash
SOURCE_COMMIT="$(git rev-parse HEAD)"

python host/context_dispatch.py packet \
  --operation COMMONS-CONTEXT-GIT-SOURCE-CAPSULES \
  --objective "Handoff exact context-dispatch source without rereading the repo" \
  --main-head "$SOURCE_COMMIT" \
  --source-commit "$SOURCE_COMMIT" \
  --source-path host/context_packet.py \
  --source-path host/context_dispatch.py \
  --max-source-file-bytes 32768 \
  --max-chars 18000 \
  --out /tmp/context-packet.json

python host/context_dispatch.py verify \
  /tmp/context-packet.json \
  --git-repo .

python host/context_dispatch.py render \
  /tmp/context-packet.json \
  --git-repo . \
  --out /tmp/context-packet.md
```

The packet can now hand another worker the exact committed source capsule plus the
existing claim, coordination, durable-event, resource, provenance, pulse, and
requested-main fences.

## Boundaries

Source paths are explicit; this feature does not crawl a repository and does not
perform secret discovery/scanning. It creates no Git/GitHub/Slack/provider writes,
claims, merges, deployments, submissions, contacts, purchases, payments, or spend.
A valid packet proves only deterministic packaging and, when CLI Git verification
is used, identity with the selected local Git object database.
