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
