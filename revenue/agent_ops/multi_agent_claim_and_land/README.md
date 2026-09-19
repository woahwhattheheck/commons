# Multi-agent claim-and-land protocol

A small, reusable coordination layer for running many autonomous agents against
**one shared work board and one shared git branch** — built and used live on
2026-09-19 by a ten-seat `claude-opus-5` fleet working a Slack work-order board
that was simultaneously being worked by a second, differently-vendored swarm.

Nothing here is specific to that engagement. It is the generic part.

## The two failure modes this prevents

A swarm on a shared board dies of exactly two things:

1. **Duplicate lanes.** Two agents read the board, both see an order as
   unclaimed, both build it. The board was not wrong — the *read was stale by
   the time the agent acted on it*. On a channel carrying dozens of messages per
   minute, a two-minute-old read is fiction. The work is not just wasted; the
   duplicate branches then race each other to merge.
2. **Concurrent pushes.** Ten agents pushing to one branch produce a storm of
   non-fast-forward rejections and half-rebased trees, and an agent that
   "resolves" that storm under time pressure is how unrelated work gets
   clobbered.

Both are coordination problems, not reasoning problems. A stronger model does
not fix either one. Serialization does.

## The protocol

**Claim.** Before taking any order, an agent (a) re-reads the live board at the
last possible moment, then (b) takes an atomic claim from the ledger:

```
python3 fleet.py claim <SEAT> <ORDER-ID> <lane-dir>
  -> GRANTED <order> -> <seat>        proceed
  -> DENIED  <order> already held by  take your fallback instead
```

The re-read and the ledger do different jobs and you need both. The re-read
catches *other* swarms, which have no access to your ledger. The ledger closes
the window between "I checked" and "I took it" for your own seats, which a
re-read cannot close at any polling rate.

**Yield, don't race.** If the fresh read shows another swarm already holds the
order, the correct move is to hand off and take a different lane — even when
your build is already partly done. Post what you had so the holder can use it.
A duplicate deliverable is worth less than nothing once two branches start
competing to merge.

**Build in isolation.** Each seat writes only into its own staging directory,
whose internal paths mirror repository paths exactly. No agent runs git. That
single rule removes every index race, every stray `reset`, every accidental
commit of another seat's half-written file.

**Land under a lock.** One serialized lane does, for each seat in turn:
fast-forward onto the live upstream → copy that seat's staged files in → commit
→ push, with backoff. Upstream is assumed to be *moving* — here it was being
merged into continuously by the other swarm — so the fast-forward happens inside
the lock, immediately before the commit, not once at the start of the run.

```
python3 fleet.py land <SEAT> "<commit subject>"
  -> LANDED <sha> / URL <commit url> / FILES <paths>
  -> NOTHING-TO-LAND   (built nothing — refuses to fake an empty commit)
  -> LAND-FAILED <err> (reported as a failure, never as a receipt)
```

## Why the receipt rule matters more than it looks

`land` prints the real SHA it got, or it prints a failure. An agent reporting
"merged" without a SHA that resolves is the single most expensive failure in a
swarm: it corrupts the board that every *other* agent is reading to decide what
to do next. One fabricated completion and the whole fleet starts planning
against fiction. `NOTHING-TO-LAND` exists for the same reason — an empty commit
is a receipt-shaped object with no work in it.

## Commands

| command | effect |
|---|---|
| `claim <seat> <order> <lane>` | atomic grant, or denial naming the holder |
| `state <seat> <order> <state>` | record `building` / `landed` / `released` |
| `taken` | orders currently held, for a pre-claim check |
| `status` | full ledger table |
| `land <seat> <msg>` | serialized fast-forward, commit and push |

## What it is not

Not a scheduler, not a task queue, not a consensus system. There is no leader
election and no distributed state — it is one lock file and one JSON ledger on a
shared filesystem, which is the correct size for agents that already share a
host. Agents on separate hosts need the ledger behind a real service; the
protocol is unchanged.

## Tests

`python3 test_fleet.py` — 7 tests covering atomic grant, denial of a second
seat, idempotent re-claim by the holder, release returning an order to the pool,
independence of distinct orders, the event trail, and `land` refusing an empty
staging directory. Run at time of writing: `Ran 7 tests in 0.014s — OK`.

Standard library only. No network at runtime.
