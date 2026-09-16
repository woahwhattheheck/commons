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

`git_source.commit` is always the exact caller-selected source commit. The sealed
packet deliberately stores no historical `main` observation: a later verifier can
reconstruct committed objects, but cannot reconstruct which ref value a compiler
claimed to have observed earlier.

Packet verification checks the semantic SHA-256 and packet budget. The CLI's
`verify` and `render` commands additionally re-read the exact commit and requested
blobs from `--git-repo`; content identity, blob identity, mode, byte count, and any
included text must still match. Only after those checks do they read the current
local `refs/heads/main`. That comparison is emitted as `LIVE_UNSEALED` in verify
output and as **Observed current main (live, unsealed)** in Markdown. It is fresh
presentation metadata, outside the packet digest, and may change immediately after
observation. A later main advance never relabels the capsule or changes its committed
source identity.

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

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../commercial.html). Not remints of tip SKUs.

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite newbot-ground-md-live-cash-20260916-09 — do not remint. Cite grok-ground-md-larger-fixed-20260916-01.
