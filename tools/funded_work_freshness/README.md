# Funded-work freshness fence

`funded_work_freshness.py` is a read-only preflight for advertised bounties,
rewards, and other funded work. It treats marketplace/aggregator state as
**discovery evidence only** and fails closed until one canonical GitHub issue or
pull request is freshly bound.

The receipt records the advertised amount separately from canonical evidence and
classifies the candidate as:

- `actionable`: canonical item is open, fresh, unassigned, unclaimed, has no
  active cross-referenced PR, and still exposes matching sponsor/amount and
  acceptance evidence;
- `occupied`: assignment, visible claim, or active competing PR exists;
- `stale`: canonical item is closed, deleted/missing, or older than the configured
  freshness window;
- `ambiguous`: evidence is incomplete, rate-limited, contradictory, unfunded,
  underspecified, or security-sensitive.

Security-sensitive candidates are routed to `research_only`; they are never
qualified directly for implementation by this gate.

## Usage

```bash
python3 funded_work_freshness.py \
  'https://example.invalid/advertised-bounty' \
  --platform example \
  --amount 500 \
  --currency USD \
  --observed-at 2026-09-13T06:30:00Z \
  --output receipt.json
```

For a board that does not expose a unique GitHub link in its HTML, provide the
explicit target with `--canonical-url`. A `GITHUB_TOKEN` or `GH_TOKEN` is used
only for authenticated read requests when present.

Exit codes: `0` actionable, `3` occupied, `4` stale, `5` ambiguous, `2` invalid
CLI input. The tool never comments, claims, contacts a sponsor, mutates a payment
provider, or equates an advertised amount with accepted/paid revenue.

## Batch intake and short-lived cache

`funded_work_batch.py` accepts JSONL so a swarm or queue can qualify many funded
leads without repeatedly fetching the same canonical GitHub evidence. Exact input
duplicates are evaluated once. Distinct discovery rows that resolve to the same
canonical issue still retain their own advertised amount/policy checks, while the
underlying read-only GitHub responses are memoized for the duration of the batch.

```bash
cat candidates.jsonl | python3 funded_work_batch.py \
  --input - \
  --output batch-receipt.json \
  --cache .funded-work-cache.json \
  --cache-ttl-seconds 60 \
  --max-cache-entries 256
```

Each JSONL row must contain `candidate_url`, `platform`, `advertised_amount`, and
`currency`; it may also contain `canonical_url`, `max_age_days`, and
`max_visible_claims`. Input is validated in full before any network request.
The batch report preserves every single-item receipt, groups rows by canonical
GitHub URL, and records fresh evaluations, duplicate hits, persistent-cache hits,
network fetches, and in-batch memo hits.

The persistent cache is opt-in and deliberately short-lived. Cache keys bind the
normalized candidate, advertised amount/currency, canonical hint, and policy
limits. Expired, future-dated, malformed, candidate-mismatched, or digest-corrupt
entries are misses and force fresh canonical reads. **Actionable receipts are
never served from persistent cache** because assignment/claim state can change at
any moment; positive authority always gets a fresh canonical read. Occupied,
stale, and ambiguous receipts may be reused only within the configured TTL, which
must be finite and between 0 and 3600 seconds. Cache writes are atomic and bounded
by `--max-cache-entries`; a corrupt cache file is ignored rather than trusted.
`--cache-ttl-seconds 0` disables persistent-cache reads while retaining in-batch
HTTP memoization.

When file paths are used, `--input`, `--output`, and `--cache` must name distinct
filesystem objects. Direct, symlink, and existing hardlink aliases fail before any
canonical network read. Output/cache leaf symlinks and symlinked existing ancestor
directories are rejected rather than silently followed. The ancestor walk is
repeated after directory creation and immediately before publication so a parent
replaced during long-running qualification does not redirect the report or cache.
A file report and cache are staged and fsynced before publication; if a normal
in-process replacement fails partway through, already-replaced targets are rolled
back to their exact pre-existing files (or removed if they were newly created), so
the command does not leave a mixed old/new report-cache pair. Stdout cannot
participate in filesystem rollback, so when `--output -` is used an optional cache
file is committed before the report is emitted.

Batch exit code is `0` when the report completed successfully even when individual
rows are occupied/stale/ambiguous; each row carries its own authoritative status.
Invalid batch input exits `2` before qualification.

## Tests

```bash
python3 -B -m unittest discover -v
python3 -O -B -m unittest discover -v
python3 -m py_compile *.py
```

Network reads reject credentials, loopback/private/link-local destinations (including
redirect targets), responses over 2 MiB, and pagination beyond ten pages. Sponsor,
amount, and acceptance decisions use only the issue body plus comments from the
issue author, repository collaborators/members/owners, or recognized sponsor bots;
untrusted solver comments can establish occupancy but cannot manufacture funding.
