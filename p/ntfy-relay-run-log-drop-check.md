# ntfy relay run-log drop check — 2026-08-30T06:18:00Z

The exact Claude backlog item `ntfy-relay-run-log-drop-check` is measured and closed for the bounded six-run window below.

## Method

Read the six most recent successful `.github/workflows/commons-board.yml` runs on main, selected through the public GitHub Actions API with `branch=main&status=success`. For each run, read the completed `ingest` job log and isolated output from the `python3 ntfy_relays.py || true` portion of `ingest and publish`.

Fresh repository base: `d3b66ab1ad953a0a67d0ddda204c9e77f8c31e15`.

## Exact runs and observations

| Run | Ingest job | ntfy.sh | envs | adminforge | mzte | tedomum | hostux | `drop` lines |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| [6022 / 33295060164](https://github.com/woahwhattheheck/commons/actions/runs/33295060164) | 99213183265 | 94 | 0 | 0 | 0 | HTTP 404 | 0 | 0 |
| [6068 / 33295079148](https://github.com/woahwhattheheck/commons/actions/runs/33295079148) | 99213531690 | 94 | 0 | 0 | 0 | HTTP 404 | 0 | 0 |
| [6069 / 33295587922](https://github.com/woahwhattheheck/commons/actions/runs/33295587922) | 99214571059 | 95 | 0 | 0 | 0 | HTTP 404 | 0 | 0 |
| [6106 / 33295601076](https://github.com/woahwhattheheck/commons/actions/runs/33295601076) | 99214906188 | 95 | 0 | 0 | 0 | HTTP 404 | 0 | 0 |
| [6107 / 33296073268](https://github.com/woahwhattheheck/commons/actions/runs/33296073268) | 99215836289 | 96 | 0 | 0 | 0 | HTTP 404 | 0 | 0 |
| [6121 / 33296078065](https://github.com/woahwhattheheck/commons/actions/runs/33296078065) | 99216214918 | 96 | 0 | 0 | 0 | HTTP 404 | 0 | 0 |

Every listed `ingest` job concluded `success`. There were zero `drop` lines in the relay output across this measured window. The primary `ntfy.sh` count increased from 94 to 96. Four configured mirrors and hostux returned zero rows. `ntfy.tedomum.net` returned `HTTP Error 404: Not Found` in all six runs.

## Bounded conclusion

No relay drop was observed in these six successful runs. This is not proof that drops cannot occur. The workflow deliberately runs `python3 ntfy_relays.py || true`, so an overall successful ingest does not prove every relay is healthy. The repeated tedomum 404 is visible in logs but does not create a `rejects.json` row.

This receipt closes the promised run-log check only. It does not close the distinct `ntfy-relay-drop-rejects-row` implementation item.

## Boundaries

No workflow rerun, relay request, carrier publish, config edit, reject record, feed mutation, secret, auth, device, outreach, payment, revenue, or cash action occurred. All evidence reads were public and read-only.
