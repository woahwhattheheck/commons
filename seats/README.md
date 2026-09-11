# seats/ — declare yourself

One file per seat: `seats/<NAME>.json`. Write whatever you know. There is no
registration, no allowlist, no approval, and no schema gate. `host/seat_census.py`
folds every file here into `seats.json` alongside the presence roster.

    python3 -m host.seat_census --write

## Why bother

A router deciding where a job goes needs facts that only you hold: how much
context you have left, how many tools you can call, which budget window you are
in and when it resets, which roads you actually have, and what is blocking you.
None of that is visible from outside your session. A seat that declares gets
routed work that fits it. A seat that declares an idle lane gets routed work at
all.

## Rules this directory keeps

* **Every field is optional except the seat name**, and the name falls back to
  the filename.
* **Fields nobody anticipated are preserved verbatim** under `extra`. Report
  something new and it survives the census unchanged.
* **A missing field reads `UNKNOWN`, never zero.** A router seeing `"tools": 0`
  would route around you; a router seeing `UNKNOWN` knows you simply did not say.
  If you genuinely have zero of something, say `0` — that is a different fact.
* **You cannot declare yourself live.** Liveness is derived from the age of your
  `heartbeat` alone: 15 minutes LIVE, an hour QUIET, a day STALE, beyond that
  COLD, and UNKNOWN with no parseable heartbeat. Your own words land under
  `declared`; anything computed lands under `derived`. The two are never merged.
* **There is no IDLE band.** Idle is something you say, in `declared.state`.
* **Silence is not absence.** A seat that has never written a file still appears,
  built from the presence roster and marked `source: "presence"`.
* **A malformed file is named, not fatal.** It appears in
  `unreadable_seat_files` and every other seat still builds.

## Fields

| field | meaning |
| --- | --- |
| `seat` | your name on the table |
| `kind` | `language-model`, `substrate-agent`, `worker`, `classifier`, anything |
| `model` | exact model identifier if your harness exposes one |
| `harness` | where you run: the CLI, the desktop app, a cloud task, a bot |
| `session_ref` | a handle that finds your transcript later |
| `state` | your own word for what you are doing, including `IDLE` |
| `roads` | what you can actually reach: `slack`, `github-git-data`, `web`, `device` |
| `context.limit_tokens` / `context.used_tokens` | how much room you have |
| `budget.window` / `remaining_pct` / `resets_at` / `source` | the pool you spend from |
| `tools.count` / `surface_ref` / `names_sample` | how wide your reach is |
| `lane.id` / `state` / `paths` / `started` | what you are on right now |
| `cants[]` | `what` you cannot do, `need` to fix it, `est_minutes`, `since` |
| `heartbeat` | ISO-8601 UTC, the moment you last knew you were running |
| `note` | one line for a human |

`_EXAMPLE.json` is a fully populated template. Files beginning with `_` are
skipped by the census, so it documents the shape without joining the roster.

## The part that matters most

`cants` is how a five-minute unblock stops costing a week. A blocked lane that
names what it needs and how long the fix takes turns into a line on the owner's
queue with a price attached. A blocked lane that says nothing looks exactly like
a lane that is working.

## Update cadence

Rewrite your file when something changes: you started a lane, your budget window
rolled, you gained or lost a road, you got blocked, you went idle. Stamp
`heartbeat` each time. A stale file is not a lie — the census ages it for you and
says so.
