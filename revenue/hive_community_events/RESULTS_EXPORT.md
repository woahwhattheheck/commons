# Download a finished Lantern leaderboard

This is an additive operator workflow for the existing Lantern application and
SQLite database, not another event store or scoring engine. It uses `Store.state`
for the native event phase and competition ranks, including ties and players who
submitted no answers. It does not finish events or change their records.

## Export from an existing workspace

Run beside `app.py` in `revenue/hive_community_events` using Python 3.10 or newer:

```sh
python -B results_export.py --db /path/to/events.sqlite3 \
  --event EVENT_REFERENCE --format csv --output leaderboard.csv
python -B results_export.py --db /path/to/events.sqlite3 \
  --event EVENT_REFERENCE --format json --output leaderboard.json
```

Replace `EVENT_REFERENCE` with the event reference in its Lantern URL or event
list. The database must already exist. Finish through the existing application,
or let the scheduled end pass. Scheduled/open events fail without creating an
output file. Unknown events preserve the application's not-found behavior.
Existing output paths are never replaced; choose a new filename for a later copy.
Exit status is 0 on success and 2 on a handled input/storage/output error.

The database is opened with SQLite `mode=ro` and `query_only=ON`. The exporter does
not initialize schemas or write event data. It reads committed WAL changes, not
pending transactions; SQLite may still use its ordinary WAL coordination files.
Keep the application's database and any live WAL files together.

## What is in the downloads

JSON is UTF-8 with schema `lantern.results.v1`. It contains public event metadata,
the participant count and the final leaderboard. Names and metadata are retained
exactly as stored by Lantern. Export timestamps are deliberately absent, so an
unchanged finished event has identical output bytes across repeat exports.
The `ends` value is the scheduled end, not a fabricated manual-finish timestamp.

CSV is UTF-8 with a BOM and CRLF records. Its columns are:
`event_id,event_title,room,rank,display_name,points,answered`.
It preserves native ordering and tied ranks such as 1,1,3; same-name participants
remain separate rows. An empty event produces a header-only CSV; use JSON to keep
that event's metadata as well. Quoted commas, quotes and multiline names round-trip.
Common formula-like text prefixes receive an apostrophe in CSV for spreadsheet
use. That transformation is intentional; JSON is the lossless text alternative.

Neither format exports participant reconnect references, personal answer rows,
question text, answer keys or unrelated events. Names and scores are still
participant information: retain/share downloads only for the community's intended
purpose. They are unencrypted and are not anonymized or verified identities.

The writer stages a complete file and publishes it with a same-filesystem hard
link. An existing file, directory or dangling link causes refusal, including when
another writer wins a race. Staging files are removed after success or failure.
A filesystem without hard-link support returns an error; there is no fallback
that could replace an existing file. This is atomic visibility, not a promise of
power-loss durability or a multi-file transaction.

## Application integration

An existing route can call `export_bytes(store, event_id, "csv")` or `"json"` and
send the returned bytes with `text/csv; charset=utf-8` or
`application/json; charset=utf-8`. `results_document` returns the allowlisted
Python object. Neither API mutates the supplied store. The native `Problem(409)`
means results are not final. This slice does not change the browser or HTTP routes;
its delivered end-user workflow is the command-line download above.

## Focused acceptance

```sh
PYTHONWARNINGS=error::ResourceWarning python -B -m unittest -v test_results_export.py
```

The suite uses the actual Lantern Store, SQLite transactions and WAL, fresh CLI
processes and filesystem operations. No live community data, browser acceptance,
hosted deployment, external platform or paid service is claimed.
