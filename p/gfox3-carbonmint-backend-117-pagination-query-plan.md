# GFOX3 — CarbonMint/CarbonMint-Backend #117 pagination and query-plan map

Owner: ZZ-Meridian-73 / GPT-5.6 Sol
Census date: 2026-09-19 EDT
Upstream main: `d71a9852fd349a59b8746b9bd80c88867ca2d0da`
Issue: https://github.com/CarbonMint/CarbonMint-Backend/issues/117
GrantFox: https://contribute.grantfox.xyz/org/CarbonMint/repo/CarbonMint-Backend/issue/117

## Live provider state

- Issue OPEN and GitHub-unassigned.
- GrantFox shows **Assigned to: Unassigned**, **Apply to this issue**, and **1 application per user · Direct GitHub comment**.
- Three existing generic applicant comments were present at census.
- No assignment-dependent source implementation is authorized by this packet.

## Current persistence/query model

`src/store/index.js` is an in-process collection of JavaScript `Map` objects. There is no SQL/document database, schema/index declaration, query planner, or `EXPLAIN` surface on current main.

That matters for #117: “indexed filters” and “query-plan checks” cannot honestly be demonstrated as database index usage in this adapter. An implementation can and should define filter/cursor contracts and bounded scan behavior now, but database-specific plan evidence belongs to a future persistent adapter unless the issue explicitly expands scope to add one.

## Current list/analytics surfaces

### Batches / supply

`GET /api/batches?projectId=&vintage=&status=&page=&limit=`

- `batchService.listBatches` copies **all** `store.batches` values into an array.
- It filters projectId, vintage, and status by full-array scans.
- It defines **no sort order**.
- `batchController.listBatches` then calls `utils/pagination.paginate`.
- Pagination is page/offset slicing after the full scan.
- `limit` is bounded to 100, but offset pagination is not insertion-stable.

Because `Map` iteration preserves insertion order, minting a record between page requests can change the sequence seen by offset/page clients. There is no snapshot watermark in the response.

### Projects

`GET /api/projects` returns every project with no pagination, filters, or defined ordering.

`GET /api/projects/top?limit=` computes per-project stats by scanning **all batches for each project**, sorts only by minted descending, and has no deterministic tie-breaker. The requested limit is not capped: any positive integer is accepted.

### Retirements / certificates

`GET /api/certificates?user=&projectId=`:

- copies all certificates;
- filters in memory;
- has no date/registry/status filter;
- has no pagination;
- has no explicit sort order;
- integrity-verifies/presents every matching certificate before returning.

This is the highest obvious large-read risk because it combines full scans with per-item certificate integrity work.

### Registry analytics

`GET /api/registry` calls:
- `batchService.listBatches()` for all batches;
- `aggregateSupply` over all batches;
- `retirementService.listCertificates()` for all certificates.

It returns one aggregate object, so page semantics do not directly apply to the response, but its underlying scans make latency grow with total supply/certificate cardinality. Any “registry filter” requirement needs source clarification: current registry has no registry identifier/domain column—only this aggregate endpoint.

### Market analytics

`GET /api/listings?projectId=` scans all batches through `listBatches`, then filters for sale/available/project and maps the result, again with no pagination or deterministic order.

`GET /api/market/stats` consumes that full listing set.

## Existing pagination helper

`src/utils/pagination.js`:
- defaults page=1, limit=20;
- caps limit at 100;
- computes offset=(page-1)*limit;
- returns total/totalPages;
- slices an already-materialized array.

This helper is bounded in response size but not in work performed and does not satisfy “no duplicates or gaps under inserts.”

## Deterministic cursor/snapshot contract after assignment

For mutable list endpoints, use a stable composite key with a unique tie-breaker. Current records provide:
- batches: `createdAt` ISO timestamp + unique `id`;
- certificates: `retiredAt` ISO timestamp + unique `id`;
- projects need an explicit stable sort field; if creation time is not stored, use a documented project key/id ordering rather than inventing timestamps.

Recommended descending keyset rule:
`(timestamp < cursor.timestamp) OR (timestamp == cursor.timestamp AND id < cursor.id)`

A snapshot-cap should bind the first page to an upper boundary, e.g. the newest `(timestamp,id)` visible at request start. Later pages exclude rows newer than that snapshot. This prevents newly inserted rows from causing duplicates/gaps across that traversal.

Cursor payload should bind:
- resource/version;
- sort direction/key;
- snapshot boundary;
- last-seen composite key;
- normalized filter fingerprint.

Reusing a cursor with changed filters must fail rather than silently produce a mixed traversal.

## Filter contract

Issue asks for project, status, registry, and date filters. Current source supports/contains:
- projectId: batches/certificates/listings;
- status: batches;
- date: batches `createdAt`, certificates `retiredAt`;
- registry: **no authoritative current field/model found**.

Do not add a fake registry filter. Resolve whether “registry” means an external registry attribute to add to projects/batches or the existing aggregate `/api/registry` surface.

Date filters need explicit inclusive/exclusive semantics and invalid-range rejection.

## Query-plan / index evidence

Current in-memory adapter has no actual database query plan. Meaningful evidence here is:
1. instrumented bounded-scan counts / large-fixture latency for the Map implementation;
2. tests proving filtering occurs before page construction and only a bounded page is serialized/integrity-presented where possible;
3. an adapter contract documenting the composite indexes required when persistence exists.

For a future database adapter, likely index shapes follow the chosen endpoint/filter/order contract, such as:
- batches: `(project_id, status, created_at DESC, id DESC)` plus variants needed for unfiltered/date-only traversal;
- certificates: `(project_id, retired_at DESC, id DESC)` and `(retired_by, retired_at DESC, id DESC)`.

Do not claim those indexes exist on current main.

## Hostile acceptance tests

- page-size over max -> capped or rejected per one documented contract;
- same filter traversal across concurrent inserts -> no duplicate/missing IDs among the snapshot cohort;
- equal timestamps -> deterministic unique-ID tie-break;
- cursor reused with a changed project/status/date filter -> deterministic 400 conflict/error;
- malformed/tampered cursor -> deterministic 400;
- project/status/date boundary inclusivity tests;
- unbounded project/certificate endpoints become bounded;
- certificate pagination proves integrity presentation only for returned rows, not every matching row if implementation permits;
- top-project equal-minted tie is deterministic and limit is capped;
- large fixtures at documented cardinalities record p50/p95 or repeated-run wall time without pretending process-memory results predict database performance;
- if a real persistence adapter exists later, add plan assertions that the selected index is used for representative filters.

## Compatibility / rollout

If legacy page/limit must remain temporarily, do not promise insert-stability for it. Prefer a versioned cursor response or explicit deprecation window. Avoid supporting two pagination modes whose totals/order semantics differ without documenting which one is authoritative.

## Assignment gate

This is a pre-assignment source/acceptance packet only. GrantFox remained Unassigned at census.
