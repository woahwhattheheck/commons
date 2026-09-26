# Repository portfolio refresh

`repository_portfolio.json` is an observation of the authenticated owner's
repositories, not a live feed. Its `scope.affiliation` is `owner`; counts do not
claim to include every collaborator or organization repository the account can
access. Private repositories contribute only a count.

The September 26 capture contains 62 repositories: 46 public and 16 private.
There are 44 observed public heads and two explicitly empty repositories. Seven
public default branches are not `main`. The backup's currentness remains
unverified: reading its branch head does not prove mirror completeness.

## Use the existing projection

```sh
python3 host/repository_portfolio.py inventory/resources/repository_portfolio.json --max-age-hours 24
```

Choose the age threshold for the task. Validation without `--max-age-hours`
checks internal consistency only. Historical snapshots remain usable without
pretending their heads are current. Exit 2 reports invalid, stale, or future
observations clearly.

## Capture fresh source facts

Use the existing authenticated GitHub connector or shared provider reader.
This builder performs no provider calls and adds no poller or schedule.

1. Enumerate `list_repositories_by_affiliation(affiliation="owner")`, recording
   page size, offsets, row counts and observation times. Continue until a short
   page; preserve whether enumeration actually completed. A provider failure is
   not an empty page.
2. Retain only the public repository names, actual `default_branch`, visibility
   and archived flag. Count private repositories without retaining their names,
   branches, URLs or contents in either public artifact.
3. Read each public repository's `git/ref/heads/{default_branch}`. Percent-encode
   the branch in the URL. Record the URL, observation time, HTTP outcome and exact
   commit SHA. `PRESENT` means a successful ref read. Only the provider's explicit
   `409: Git Repository is empty.` response means `EMPTY`; a zero size, 404,
   permission error or rate limit does not. An unresolved read is `UNAVAILABLE`
   with `head_sha: null`; never carry forward an old SHA as a new observation.
   If rate-limited, stop the batch and resume through the shared provider budget.
4. Save the sanitized capture in `repository_portfolio.source.json`, following
   the existing `commons-repository-source/v1` shape. The timestamp of each head
   read is retained because listing and heads are not an atomic provider snapshot.

## Build and publish

```sh
python3 host/repository_portfolio.py inventory/resources/repository_portfolio.json \
  --build-from inventory/resources/repository_portfolio.source.json \
  --output inventory/resources/repository_portfolio.json --max-age-hours 24
```

The existing projection supplies routing roles and purpose annotations. New
public repositories become `PUBLIC_REFERENCE`. Repositories absent from a
complete fresh listing leave the current projection; their prior observation
remains in Git history. A missing canonical head or incomplete listing leaves
the previous output untouched. Writes replace the destination atomically.

Commit the source and projection together. `evidence.source_sha256` binds the
projection to the exact source bytes. Repeating the build from those bytes and
the same routing roles produces the same projection, without new API reads.
Fetching an updated source is a distinct operation from reproducing a capture.

Version 2 adds explicit default branches, `PRESENT` / `EMPTY` / `UNAVAILABLE`
head states, per-head provenance, and empty/unavailable summary counts. The
validator continues to read version 1 historical projections. Consumers must
check `head_state` before using a nullable `head_sha`. `CANONICAL` identifies the
repository's role; freshness comes from observation timestamps, not that label.

Repository observations do not establish task completion, sponsor acceptance,
award approval, payment, deployment or disaster-recovery readiness.
