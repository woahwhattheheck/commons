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
  --canonical-url 'https://github.com/owner/repo/issues/123' \
  --observed-at 2026-09-13T06:30:00Z \
  --output receipt.json
```

Direct GitHub issue/PR URLs require no separate canonical argument. Automatic
candidate-page discovery is deliberately restricted to recognized sponsor-owned
host suffixes (`algora.io`, `opire.dev`, `polar.sh`, `issuehunt.io`, and
`gitcoin.co`). Arbitrary marketplace/aggregator URLs remain supported, but must
supply `--canonical-url` so untrusted board hostnames are never fetched merely to
discover their GitHub target.

The HTTP transport independently resolves each requested hop to public addresses
and connects to the validated IP while preserving the original hostname for TLS
verification and the `Host` header. Redirects from recognized sponsor pages must
remain inside that sponsor's label-aware domain suffix; other reads may redirect
only within the same host. This keeps the landed DNS-pinned socket boundary while
removing arbitrary board DNS from automatic discovery.

A `GITHUB_TOKEN` or `GH_TOKEN` is used only for authenticated GitHub API read
requests when present.

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
amount, and acceptance decisions use only issue/comment prose authored by repository
owners, members, collaborators, or recognized sponsor bots; merely creating the issue
does not grant funding authority. External issue text remains visible to security
classification and occupancy logic, but cannot manufacture sponsor, amount, or
acceptance evidence.
