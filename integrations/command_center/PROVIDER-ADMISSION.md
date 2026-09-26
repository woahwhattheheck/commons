# Shared provider publication admission

`host/provider_budget.py` admits cooperating GitHub publishers through the
existing `request-budget.sqlite3` ledger. Use one **shared state directory** for
all callers and, when available, the command center's existing state directory.
This is local process coordination, not a quota pool across separate machines.
Do not copy the database into each checkout. Canonical work claims stay in
`state/claims`; this lease covers provider capacity only.

The coordinator configures capacity once. Workers cannot raise it through an
acquisition. Reducing capacity lets existing admitted work finish and blocks new
holders until the active count drops below the new cap.

```sh
python host/provider_budget.py --state-dir /shared/command-center-state configure --capacity 3
python host/provider_budget.py --state-dir /shared/command-center-state status
python host/provider_budget.py --state-dir /shared/command-center-state acquire --holder lane-f
```

Successful acquisition returns `lease_id`, `holder`, `scope`, `capacity`, and
`expires_at`. Each concurrently executing publisher needs a distinct holder.
Repeated acquisition by the same holder returns its existing lease without
extending it or occupying another slot. Keep the returned lease ID.

Immediately before **each connector write**, renew using that exact ID:

```sh
python host/provider_budget.py --state-dir /shared/command-center-state renew --holder lane-f --lease-id LEASE_ID
```

Proceed only on exit 0 and `ok: true`. Exit 75 means no admission: the JSON
contains `reason` (`capacity_exhausted` or `rate_limited`) and
`retry_not_before`. Schedule a later continuation; the CLI never sleeps. The
capacity timestamp is the earliest current lease expiry, an advisory retry time,
not a reserved future slot. Earlier release may free capacity sooner.

The default lease lifetime is 300 seconds; `--ttl-seconds` accepts 1–3600. Choose
a lifetime longer than an individual connector call's timeout. Expiry cannot
cancel an already in-flight remote write. A paused/expired holder must stop
effects, preserve stable operation IDs, reconcile uncertain provider outcomes,
and obtain new admission. Old lease IDs cannot renew or release replacements.

On an observed secondary/unknown GitHub limit, record its actual evidence:

```sh
python host/provider_budget.py --state-dir /shared/command-center-state limited --retry-after 120
# If no provider deadline was exposed, omit --retry-after; bounded fallback applies.
```

This uses the existing `github:GET` provider-wide cooldown identity, also honored
by command-center reads. Every publication acquisition and renewal checks it,
plus the existing `github:GET:core` primary cooldown. For confirmed primary core
quota exhaustion, add `--primary-core` and the observed `--reset-at` epoch.
Never invent a deadline or use primary classification for a secondary limit.

Release in a `finally` path after finishing or deferring:

```sh
python host/provider_budget.py --state-dir /shared/command-center-state release --holder lane-f --lease-id LEASE_ID --successful
```

Use `--successful` only after confirmed provider success; omit it on failures,
deferrals, or uncertainty. This resets expired fallback streaks while preserving
any newer active limit. Release is idempotent and requires both holder and ID.
The CLI makes no provider calls, grants no publication authority, and starts no
worker, timer, service, or paid compute.
