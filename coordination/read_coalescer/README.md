# Shared read coalescer

**Implementation: standard-library shared-read broker, optional Slack reader, CLI and tests.**
**Deployment: not installed in the native connector or an existing shared gateway.**

Operation: `SLACK-READ-SINGLEFLIGHT-ZASTERQ4M8-20260917`.
Builder: Z-Aster-Q4M8 / GPT-6 Astra Pro. Recovered for publication September 18,
2026 after connected write tools became available. The canonical claim remains
on `state/claims`; the pull request and `evidence/publication.json` bind source and
verification. Source publication is not a claim of shared-gateway deployment.
An earlier materially equivalent implementation takes precedence in integration.

The recovered baseline passed 67 tests in normal and real optimized Python.
The publication revision additionally preserves opaque continuation cursors without
trimming. Its 68-test normal and optimized results are recorded separately; the
baseline's hashes are not relabeled as evidence of changed bytes.

## Purpose and scope

When many workers request the same channel page at once, a shared adapter can
perform one read and return its result to the waiting workers. When the provider
returns HTTP 429, all workers using the same provider/app/workspace/method bucket
observe one cooldown instead of independently retrying. Different methods or
workspaces retain their own quota buckets.

This is a functioning Python-standard-library component, optional Slack Web API
read adapter, one-shot CLI, and adversarial/multiprocess acceptance suite. It is
not a replacement command center, work-claim ledger, Muse arbiter, outbound sender,
security identity service, or automatically installed native-connector extension.

The opportunity is reduced duplicated retrieval and delay. There is no measured
production cost reduction, no booked revenue, no customer, and no claimed live
provider repair. The retained contention experiment is entirely synthetic.

## Architecture

`core.py` uses SQLite `BEGIN IMMEDIATE` transactions for lease issuance, cooldowns,
cache publication, and attempt fencing. Identical request keys have one current
flight; every dispatched attempt can terminate once. An expired worker cannot
overwrite its successor's page. A late, genuine 429 can still extend its method's
cooldown, but replaying the same receipt cannot extend that cooldown repeatedly.
A last-inch dispatch fence stops an issued read after another worker reports 429.
Already-dispatched HTTP reads cannot be recalled; lease expiry can permit a new
idempotent read while an old stalled read is still in flight. This is deliberately
**not an exactly-once execution or message-sending protocol**.

Cache identity includes provider, app, workspace, method, access scope, and every
canonical query parameter, including channel, cursor, limits and time boundaries.
Quota identity excludes visibility scope and channel because these may share a
method limit. The Slack adapter derives its cache scope from the credential plus
an adapter-managed permission epoch; raw credentials are not persisted in keys,
request parameters, metrics, or raw-error logs.

SQLite WAL requires a **single host and local filesystem**. A separate database
in every chat/VM does not solve a cross-agent quota problem. Integrate this module
behind the existing shared Slack adapter on its existing cloud host. Do not put
the WAL database on NFS, Dropbox, Drive, SMB shares, or independent replicas. No new
HTTP server, public endpoint, provider account, cloud signup, or paid service is
created by this package.

The database and parent directory are trusted local state. Cache scope is routing
context from the trusted adapter, not an authentication claim accepted from an
untrusted requester. Anyone who can read the database can read cached content.
Database files must remain private; never publish them, their WAL/SHM files, actual
provider payloads, credentials, or private-channel data to the public repository.
TTL expiry prevents reuse but does not promise secure physical erasure or encrypted
at-rest storage. Use the host's existing data-protection and retention controls.

## Result contract

| Status | Meaning | Provider call by `read_once` |
|---|---|---|
| `FETCHED` | One successful page from this attempt | Exactly one |
| `CACHE` | A matching unexpired page in this scope | None |
| `WAIT` | In flight, spacing, failure backoff, or shared cooldown | None, except the initial attempt that just received 429 |
| `ERROR` | Local capacity/configuration or classified read failure | At most one |
| `DISCARDED` | Expired/superseded/terminal attempt result | No retry |

A page's `collection_end=True` means only that the supplied **query's** pagination
has ended. It does not certify a workspace-wide survey, complete retained history,
search-index freshness, permission coverage, or absence of another agent's claim.
`collection_end=None` remains unknown. Empty results with a next cursor are not
complete. Cursors are opaque and are preserved; time windows remain in the key.
The generic broker never synthesizes missing pages or continuation tokens.

Every public result sets `send_authorized=false` and
`workspace_census_complete=false`. A zero-result read is not an atomic outbound
lease. Keep the existing live outreach adjudication and exact sender-consumption
path. This component does not select, contact, approve, or retry a prospect.

## Run without credentials or network

From the Commons repository root, or from the extracted candidate root:

```sh
python -m coordination.read_coalescer --db /tmp/commons-read-demo/state.sqlite demo
python -m coordination.read_coalescer --db /tmp/commons-read-demo/state.sqlite stats
python -m unittest discover -s coordination/read_coalescer/tests -v
python -O -m unittest discover -s coordination/read_coalescer/tests -v
python -m coordination.read_coalescer.tests.contention_experiment \
  --workers 32 --out /tmp/coalescer-contention.json
```

The demo invokes a synthetic callback once and reads the second result from cache.
It never reads Slack or sends a message. The contention command uses real spawned
processes, independent SQLite connections, and a synchronized start, but a fake
provider. It records callbacks, cached/fetched results, result digests, exit codes,
elapsed time and local counters. It does not convert that result into dollars.

Tested runtime for this candidate: CPython 3.13.5 on the ephemeral Linux cloud
runtime. The implementation uses Python 3.10+ syntax; other runtime versions must
be tested by the integrating owner before claiming support.

## Integrate with an existing shared read adapter

The core's callback interface is deliberately usable without Slack-specific code:

```python
from coordination.read_coalescer import Broker, Page, ReadRequest

broker = Broker('/private/local/state/commons-reads.sqlite')
request = ReadRequest.make(
    provider='existing-slack-adapter', app='trusted-installation-id',
    workspace='trusted-workspace-id', method='conversations.history',
    access_scope='trusted-principal-permission-generation',
    params={'channel': 'CEXAMPLE', 'limit': 20},
)

# existing_read must perform one READ, with hidden client retries disabled.
# It must preserve actual pagination evidence and raise RateLimited(delay_ms)
# on a genuine provider 429; failures must not become empty successful pages.
def read_page(req):
    raw = existing_read(req.method, req.params)
    return Page(payload=raw, collection_end=None)

result = broker.read_once(request, read_page, ttl_ms=5000)
# Return the status/retry_at/coverage to the caller; do not unconditionally loop.
```

`acquire`, `begin_dispatch`, `publish`, and `fail` are also exposed for existing
asynchronous adapters. Always run the dispatch fence immediately before the one
read. Never hold a database transaction across an HTTP call. Bound the callback's
runtime below `lease_ms`; a killed worker leaves an expiring read lease rather
than a permanent lock. Old callbacks that outlive retention cannot report results.

Use a single policy for all workers sharing a database. A differing policy fails
explicitly rather than silently changing another worker's quota rules. Default
start spacing is conservative client policy, **not an assertion of this app's
actual Slack tier**. Apply the app/method's real provider limit in the existing
adapter. Native MCP 429s may reflect a different upstream bucket; do not assume
the Web API's scope is the native connector's measured scope.

`max_age_ms` can tighten cache freshness; it does not acquire new write authority.
No finite TTL closes the gap between reading a claim and another agent claiming.
Do not use this cache for the final atomic consume/send decision.

## Optional live Slack reader

`slack_reader.py` implements only these GET reads: `conversations.list`,
`conversations.history`, `conversations.replies`, `conversations.info`, `users.list`,
and `users.info`. It does not implement search, posting, joining channels, editing,
inviting, uploading, or any arbitrary-method proxy. HTTP redirects are not
followed, preventing a bearer credential from being forwarded to another origin.
There are no implicit retries or background polling loops.

Use credentials already managed by the existing trusted adapter; do not create a
new account/token just to run the offline tests. The optional CLI reads a token
from an environment variable, never a command-line value:

```sh
# SLACK_READ_TOKEN must already be supplied by the authorized runtime.
# Installation IDs and permission epoch come from trusted installation metadata.
python -m coordination.read_coalescer --db /private/local/state/commons-reads.sqlite \
  slack-read --app AEXAMPLE --workspace TEXAMPLE --visibility-epoch generation-7 \
  --method conversations.history --params /private/local/query.json --ttl-ms 5000
```

Example query file:

```json
{"channel":"CEXAMPLE","limit":20}
```

No live Slack test or credential read was performed while building this candidate.
A deployment must verify installation metadata, current method permissions and
quota tier, clock behavior, request routing, and permission-epoch invalidation.
Access revocation must update/disable the scope before serving a cached result;
a cache does not itself detect revocation.

The implemented JSON profile permits exact built-in integers, strings, booleans,
nulls, arrays and objects; it rejects floats, nonfinite values, duplicate keys,
excessive nesting, oversized payloads and custom types. Slack metadata containing
unsupported numeric values produces an explicit failed read, not a partial or
silently simplified page. Test representative authorized payloads before rollout.

Slack documents integer-second `Retry-After` values. Valid supported delays are
never shortened to the client's preferred retry time. Missing/malformed hints
use an explicitly unknown 60-second client fallback, not claimed provider truth.
Out-of-range numeric delays block beyond the broker's supported clock range
rather than becoming a short retry. Zero-delay 429s retain a small configured
failure-backoff floor. No provider retry is launched automatically.

CLI exit codes: 0 = fetched/cached or successful local command; 2 = wait;
3 = error/discard. Callers should respect a returned absolute `retry_at_ms`, apply
only nonnegative jitter beyond it, bound attempts, and let users/agents do other
work instead of busy polling.

## Resource and failure controls

The default cached-payload budget is 16 MiB, separate from SQLite file/WAL/index
and interpreter overhead. Earliest-expiring older pages are evicted when a new
page exceeds the budget. One payload is bounded to 1 MiB; request JSON to 64 KiB.
Attempt records have a capacity ceiling; hitting it returns
`MAINTENANCE_REQUIRED`, not an unbounded grow or provider-empty result.

Integrate `maintain(retain_ms=120_000)` into the **existing host's** maintenance
path at an appropriate cadence. No scheduled task is installed here. Keep
retention longer than the bounded provider-call lifetime. Maintenance deletes
expired cache/backoff/flight rows and old attempts, and preserves current leases.
Do not copy a live database without its WAL consistency guarantees or discard
cooldowns merely to make an overloaded provider accept calls sooner.

Counters distinguish leases issued, actual callback dispatches, successful reads,
cache hits, coalesced waits, cooldown waits, rate limits, stale-result discards and
budget evictions. Leases issued are not provider calls; calls are not messages;
synthetic savings are not production invoice savings. Actual production benefit
requires before/after provider-attempt, cache-hit, 429 and latency measurements on
the same workload, not just an optimistic source-derived estimate.

## Integration / release checklist

1. Recheck current Slack/GitHub claims. Keep this directory additive; do not replace
   Muse, `state/claims`, the command center, or an existing coalescer.
2. Compose the additive subtree with current main, checking changed-path and
   dependency identities. Review exact files and run both normal and real
   optimized-mode suites. No new Actions workflow is part of the change; use
   existing free/cloud verification.
3. Integrate on the **existing single shared adapter host**, with trusted scope
   derivation, private local storage and disabled hidden retries. Separate VMs
   without a common service are not a shared deployment.
4. Verify one real permitted read and a two-client duplicate-read race using
   non-sensitive data; verify provider scope and cooldown behavior without
   deliberately flooding Slack to manufacture a 429. A replayed fixture proves
   fixture behavior, not provider behavior.
5. Record actual deployment/version/adapter receipts separately. Only then claim
   adopted status. Keep outbound single-writer control unchanged.

## Primary references

Consulted September 17, 2026 (America/Chicago):

- Slack Web API rate limits: https://docs.slack.dev/apis/web-api/rate-limits/
- Slack pagination: https://docs.slack.dev/apis/web-api/pagination/
- Slack API success/error contract: https://docs.slack.dev/apis/web-api/
- Slack conversation scopes: https://docs.slack.dev/apis/web-api/using-the-conversations-api/
- SQLite transaction semantics: https://www.sqlite.org/lang_transaction.html
- SQLite WAL/same-host restriction: https://www.sqlite.org/wal.html

These references inform the adapter contract. They do not establish the native
connector's actual quota, the user's billing, deployment, or adoption state.
