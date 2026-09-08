# Lantern — community trivia events

Runnable scheduled-trivia slice of Slack build demand `bm-hive-20260908-038`.
The Python service, browser workspace and SQLite database form one application.
There are no runtime package dependencies, data purchases, payments or cash prizes.

## Run

Use Python 3.10 or newer in an existing cloud environment:

```sh
cd revenue/hive_community_events
python -B app.py --db /path/to/persistent/events.sqlite3 --port 8765
```

Open `http://127.0.0.1:8765` in the same environment. `--host` selects the listen
address when an existing trusted-community host supplies the network route.
This source delivery does not create a hosted deployment or incur infrastructure costs.
The database parent directory must already exist. Keep the database on persistent
storage across server restarts; do not commit participant data to the repository.

## Complete a round

1. Expand **Host a new event**. Enter a room, start/end time, title and question set.
   The initial questions are editable sample content, not a live community event.
2. Create the event and share its event URL. Participants enter a display name.
   Questions appear at the start; submitted answers are final.
3. Reopen the URL in the same browser to resume. To switch browsers, use the
   participant reference under **Your reconnect reference**. It is a record
   locator, not a password or verified identity.
4. Wait until the end or use **Shared host controls → Finish event and reveal
   scores**. The final leaderboard and correct choices remain available after
   reconnecting or restarting the service with the same database.

Times in the host form use the browser's local timezone; the API stores Unix
seconds. The server clock determines whether an event is scheduled, open or
finished. End is exclusive: at the end timestamp, new answers stop. An identical
retry of an already recorded answer remains successful after the event finishes.
Finishing is final and idempotent. An event cannot be reopened or have its
question set changed after creation.

## Scoring and persistence

One first answer per participant and question is committed in a SQLite
transaction. Concurrent identical retries return the same saved choice without
adding points. A retry with a different choice returns HTTP 409 and does not
replace the original answer. Correct choices receive the question's configured
integer points; all other answers receive zero. There are no speed bonuses.

Questions and correct choices are withheld until the scheduled start and finish,
respectively. Scores are revealed only after finish. Equal totals share rank;
the next rank uses competition ordering (1, 1, 3). Ties have a stable display
order using join time and participant reference. Participants with no answers
appear with zero points.

Use nicknames: display names and final scores are visible to the room. Hosting
and finish controls are shared by everyone with access. There is no account
system, verified identity, competitive anti-cheat protection or isolated tenant
boundary. This is a trust-based community activity, not a tournament or a public
multi-tenant SaaS deployment. Clearing browser storage does not delete server
history; preserve the reconnect reference before doing so.

## API

All mutation bodies are JSON objects. A question has `prompt`, `choices`,
zero-based `correct`, and optional `points` (default 100).

| Method | Route | Input / result |
| --- | --- | --- |
| GET | `/health` | Service liveness |
| GET | `/api/events` | Event and room list with schedule and participant counts |
| POST | `/api/events` | `title`, `room`, `opens`, `ends`, `questions`; returns event `id` |
| GET | `/api/events/{id}` | Phase, visible questions and final leaderboard |
| GET | `/api/events/{id}?member={reference}` | Same snapshot plus that participant's saved answers |
| POST | `/api/events/{id}/join` | `name` for a new participant, or `member_id` to resume |
| POST | `/api/events/{id}/answers` | `member_id`, `question`, `choice`; retry-safe first answer |
| POST | `/api/events/{id}/finish` | `{}`; finish for the whole room |

Creating an event or joining without an existing participant reference is a new
record on each request. Only answer submission, resuming and finish are
idempotent. On a lost create/join response, inspect the event list/current
participant state before initiating another create/join.

## Validation

```sh
python -B -m unittest -v test_app.py
```

The focused suite uses real SQLite databases, concurrent transactions and a real
loopback HTTP server. It covers scheduling, answer retries and conflicts,
restart/reconnect persistence, final score visibility, tied ranks, malformed
input, event separation and the create/join/answer/finish HTTP workflow.

The source was tested on Python 3.13.5: **21/21 tests passed**. The embedded
JavaScript also passed `node --check` on Node 22.16.0. A native Chromium browser
acceptance run could not navigate to the loopback service under this harness's
administrator policy; browser interaction and layout are therefore **unverified**.
Backend HTTP results do not stand in for browser acceptance.

## Remaining demand-038 work

Chess-style interactive challenges, an actual community-platform installation,
creator/customer demo, hosted availability and any paid subscription are not
part of this trivia slice. No sale, recurring revenue or customer adoption is
claimed. Extend this implementation rather than starting a second event store.

Authored by ASTRA-LANTERN using the provided cloud container and the owner's
Slack/GitHub connections. No TITAN files, simulation lanes or owner-PC files are
part of this change.
