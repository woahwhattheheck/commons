# GitHub read-rate coordinator

This is a **read-only** local coordination gateway for cooperating swarm processes that otherwise stampede GitHub with duplicate reads. It was created after live swarm work hit GitHub's secondary rate limiter while several peers were independently reading repository, pull-request, file and search state.

It does not grant, infer or proxy any GitHub write authority. The upstream provider supports `GET` only, targets the fixed `https://api.github.com` origin, rejects redirects, and exposes only the allowlisted routes in `broker.ROUTES`. There is no generic URL, HTTP-method, GraphQL, ref-write, issue-write, PR-write, merge, workflow-dispatch, visibility, billing, secrets, or administration surface.

## What it coordinates

`broker.py` stores only a credential SHA-256 fingerprint, normalized request keys, bounded cached JSON and cooldown metadata in a local SQLite database. Multiple processes sharing that database get:

- request-key singleflight so identical reads have one upstream owner;
- a short cross-process burst fence before distinct calls;
- separate primary `core` and `search` cooldown buckets;
- a principal-wide `secondary` cooldown when GitHub reports a secondary limit;
- persisted `Retry-After` / `X-RateLimit-Reset` backoff that never shortens an existing cooldown;
- namespace isolation after token rotation and fail-closed blocking after HTTP 401;
- bounded request, response, cache-age and cache-row surfaces;
- no stale cached success when a required refresh fails.

The coordinator is advisory infrastructure for processes that actually route reads through it. It cannot retroactively throttle unrelated clients that bypass the gateway.

## Run

Set two independent secrets in the environment:

```text
GITHUB_TOKEN=<read-capable token>
GITHUB_READ_GATEWAY_KEY=<64 lowercase hex chars generated independently of the token>
```

Then start on loopback only:

```bash
python tools/github_read_coordinator/gateway.py \
  --db /private/path/github-read-coordinator.sqlite \
  --expected-login woahwhattheheck \
  --port 8766
```

The gateway authenticates the GitHub token with the read-only `/user` endpoint before serving. It listens on `127.0.0.1` and accepts only authenticated `POST /read` calls to its **local** interface; every upstream GitHub request remains a `GET`.

Example local request body:

```json
{"route":"repo.get","params":{"owner":"woahwhattheheck","repo":"commons"},"max_age_seconds":30}
```

Possible broker states are `FETCHED`, `CACHED`, `BUSY`, `COOLDOWN`, `AUTH_BLOCKED`, `UPSTREAM_ERROR`, and `DISCARDED`. Every envelope includes `provider_write_authority: false`.

## Supported upstream reads

- `repo.get`
- `contents.get`
- `pull.get`
- `pull.files`
- `commit.get`
- `issues.list`
- `actions.runs`
- `search.issues`
- `search.code`

Parameters are strictly normalized. Repository paths cannot traverse; dynamic URL segments are percent-encoded; query values are generated with `urlencode`; token and arbitrary-URL overrides are impossible by schema.

## Test

From this directory:

```bash
python -m unittest -v test_broker.py test_gateway.py
python -O -m unittest -v test_broker.py test_gateway.py
python -m py_compile broker.py gateway.py test_broker.py test_gateway.py
```

The suite includes real eight-process singleflight, secondary-limit persistence across broker instances, primary bucket isolation, late/stale lease rejection, token-rotation behavior, payload/JSON bounds, path/header injection rejection, fixed-origin/no-redirect checks, and proof that the provider issues `GET` only.
