# Creator Desk multi-community hosting boundary

`multisite.py` turns the existing single-workspace Creator Desk into a **local,
fail-closed multi-community runtime**. It leaves `Store`, `OperatorAuth`, and
`app.make_server` single-tenant: every community receives an independent SQLite
generation, operator capability root, and loopback Creator Desk server. The
outer router selects exactly one tenant from an explicit HTTP `Host` registry.

This is a commercialization control plane, not a deployment promise. It does
**not** buy domains, create DNS, terminate TLS, configure an IdP, send email,
collect money, contact customers/providers, or expose the service publicly.
Those remain explicit owner/deployment decisions outside this repository.

## Platform boundary: Linux/POSIX generation custody

Multi-community isolation is intentionally stricter than ordinary pathname
validation. The host requires Linux/POSIX primitives `O_DIRECTORY`,
`O_NOFOLLOW`, `O_CLOEXEC`, dirfd-relative opens, and `/proc/self/fd`.
Unsupported platforms fail closed before a workspace is opened.

The workspace root must be an **absolute, non-root path**. Registry loading
walks its existing ancestor components from `/` with no-follow directory opens,
retains the exact root directory file descriptor, and then retains one exact
workspace directory descriptor and one exact `workspace.sqlite3` descriptor per
community. Provisioning may create the final workspace-root component, tenant
directories, and database files, but it does not recursively create an
unverified ancestor chain.

Existing Creator Desk layers receive a database path such as
`/proc/self/fd/17`, which resolves to the retained database generation. A
rename, symlink replacement, sibling-directory swap, or database hardlink swap
after validation therefore cannot redirect the later `Store`/`OperatorAuth`
SQLite open to another tenant. The registry also rechecks on startup and every
Host resolution that each logical community name and database filename still
maps to its retained `(st_dev, st_ino)` identity. Drift fails closed. Duplicate
workspace or database identities are rejected.

The retained descriptors are runtime custody, not serialized state. Closing the
registry releases them; the operator CLI closes them explicitly after
provision/validation/shutdown.

## Registry

Create a strict JSON file outside the repository. Unknown keys, duplicate JSON
keys, duplicate IDs, case-equivalent hosts, unsafe IDs, malformed authorities,
symlinked registry files, and non-finite JSON values fail closed.

```json
{
  "version": 1,
  "communities": [
    {"community_id": "makers-guild", "host": "makers.example.test"},
    {"community_id": "writers-room", "host": "writers.example.test:8443"}
  ]
}
```

Community IDs are deliberately filesystem-safe lowercase slugs. Hosts are
ASCII DNS authorities with an optional canonical decimal port. A stored port is
part of the route: `writers.example.test` does not match
`writers.example.test:8443`. IPv6 literals, URLs, userinfo, trailing dots,
whitespace/control characters, path/query/fragment syntax, and non-canonical
ports are rejected rather than guessed.

No default tenant exists. Missing, duplicate, malformed, or unknown `Host`
headers never fall through to another community.

## Provision once

Use a dedicated absolute workspace root. Its parent chain must already exist
and must not contain symlinks. The final `communities` directory may be absent;
`provision` creates that final component with mode `0700`.

```bash
cd revenue/hive/creator-toolkit
python multisite.py \
  --registry /secure/creator-communities.json \
  --workspace-root /srv/creator-desk/communities \
  provision
```

Provisioning creates one logical database name per ID:

```text
/srv/creator-desk/communities/makers-guild/workspace.sqlite3
/srv/creator-desk/communities/writers-room/workspace.sqlite3
```

Those names are only registry identities. During the operation, the actual
SQLite authority is the retained file generation reached through
`/proc/self/fd`.

For each previously uninitialized community, stdout contains a
`one_time_operator_keys` entry. **Capture each key as an owner secret and do not
redirect that output to a shared log or commit it.** Only the SHA-256 verifier
is stored by `OperatorAuth`; plaintext capabilities are never written to the
registry or control-plane state. Running `provision` again does not disclose or
rotate existing keys.

If a key must change, use the existing per-workspace `operator_auth.py rotate`
flow against that community's exact database while the service is stopped and
the workspace is under the same trusted local filesystem custody. Rotation is
intentionally not a cross-tenant multisite action.

## Validate before serving

```bash
python multisite.py \
  --registry /secure/creator-communities.json \
  --workspace-root /srv/creator-desk/communities \
  validate
```

Validation requires every derived workspace database and operator capability
root to already exist. It does not create a missing workspace root, tenant, or
capability. It reasserts retained generation identity around the existing
`Store` and `OperatorAuth` opens.

## Run the loopback router

```bash
python multisite.py \
  --registry /secure/creator-communities.json \
  --workspace-root /srv/creator-desk/communities \
  serve --host 127.0.0.1 --port 8768
```

The multisite listener intentionally accepts loopback binds only. If a trusted
reverse proxy is later placed in front of it, that deployment must preserve the
**exact validated external Host authority** and own TLS, request-size limits,
client/network policy, and public exposure. None of those controls are silently
inferred here.

A routed health check is available at `/__multisite/health`. It supports only
GET/HEAD, accepts no body, validates request framing before success, and closes
the HTTP/1.1 connection after its response. It returns only the selected
`community_id`, canonical `host`, and `status`, plus an
`X-Creator-Community` response header. It exposes no operator capability or
member data.

The existing operator `/workspace.sqlite3` download is intercepted by the outer
router in multisite mode. After operator-capability verification, it opens the
retained `/proc/self/fd` database generation directly, uses SQLite online backup
plus the existing Creator Desk snapshot integrity checks, reasserts generation
identity, and only then returns bytes. It never calls the single-tenant copy
helper's pathname `resolve()` step, which would throw away descriptor custody.
The multisite download inherits the outer 12 MiB response bound.

## Isolation and proxy invariants

The host layer keeps these hard boundaries:

- one registry ID -> one canonical Host -> one retained workspace/database
  generation;
- distinct `Store` and `OperatorAuth` instances for every community;
- a bearer key from community A is rejected by community B;
- identical member emails or operation IDs in two communities remain separate;
- directory/database generation replacement is detected before routing and
  around lower-layer startup/provision opens;
- workspace downloads snapshot the retained database descriptor directly and
  reassert identity before emitting any bytes;
- only `Authorization`, `Content-Type`, and `Content-Length` are forwarded from
  the outer request to the selected loopback app;
- hop-by-hop headers are never forwarded;
- all successful routes validate framing first; request bodies are bounded at
  12 MiB, duplicate/non-canonical `Content-Length` is rejected, and
  `Transfer-Encoding` is rejected;
- unsupported methods return 405 and close rather than reaching a tenant;
- startup failure closes already-started tenant servers; normal shutdown stops
  and closes the router and every tenant thread;
- tenant access logs stay silent so capabilities/member references are not
  copied into host logs.

The router does not add authorization to member-public routes or remove the
existing operator authorization from privileged routes. It reuses the existing
single-tenant boundary rather than inventing a second policy engine.

## Tests

From `revenue/hive/creator-toolkit` on Linux:

```bash
python -m unittest -v test_multisite test_multisite_security test_toolkit test_operator_auth test_workspace_copy
python -O -m unittest -v test_multisite test_multisite_security test_toolkit test_operator_auth test_workspace_copy
```

`test_multisite.py` covers duplicate/case-equivalent hosts, malformed
registries, unsafe/relative roots, path/symlink escapes, one-time secret
persistence, wrong-tenant bearer rejection, same-email isolation, operator
mutation isolation, explicit port routing, unknown/missing/duplicate Host,
concurrent traffic, restart persistence, loopback-only binding, and thread
cleanup. It also performs deterministic hostile swaps of a community directory
and database **between the pre-open identity check and the lower-layer
`Store` open**, proving the retained file generation is used and the subsequent
identity assertion stops startup/provision instead of exposing a sibling
community.

Raw-socket hostiles cover health-route `Transfer-Encoding`, duplicate and
oversized `Content-Length`, and a body containing a second pipelined request;
none may produce a second routed response.
