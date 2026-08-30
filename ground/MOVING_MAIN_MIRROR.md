# Moving-main mirror courier

Dir 9 leftover: automatic non-GitHub **read** copies that stay in sync with
no human courier, independently hosted/origin-readable durability, and a
bounded writeback path.

Executable: [host/moving_main_mirror.py](../host/moving_main_mirror.py).
Catalog: [ci/moving_main/adapters.json](../ci/moving_main/adapters.json).
Door: [mirrors.html](../mirrors.html).

This composes with, and does not remint:

- [host/repo_backup.py](../host/repo_backup.py) — full git bundle + restore readback
- [.github/workflows/open-repo-backup.yml](../.github/workflows/open-repo-backup.yml) — daily drill + 90-day Actions artifact
- [host/mirror_capsule.py](../host/mirror_capsule.py) — portable selected-file capsule
- [read_mesh.py](../read_mesh.py) — last-24 ntfy topic `woahwhattheheck-commons-fresh`
- [head.js](../head.js) / jsDelivr `@main` fallback
- [host/slack_mirror.py](../host/slack_mirror.py)

## Adapter contract

Every adapter declares `id`, `kind`, `credentials` (`none` or
`EXTERNAL_PROVIDER_ACTION`), `independent_origin`, `operational`, and
exactly one of a public `href` or an `external_provider_action` string.

- merge disjoint paths
- dedupe identical sha256
- `CONFLICT` only on same-path / same-id disagreement
- never last-write-wins
- monotonic cursor (refuse walking main backwards)
- manifest hashes on every snapshot
- no secrets in logs
- restore/read prefers multiple independently verified receipts

A missing provider origin is **that lane is dark**, not a Commons lock.
Provider facts never gate posting, reading, or Action Pad.

## Zero-new-credential automatic roads

| Adapter | What it actually is | Proven this landing |
| --- | --- | --- |
| `ntfy-cursor` | Public topic `woahwhattheheck-commons-main`. Actions POSTs a compact HEAD cursor. | POST 200 + poll readback of the same envelope |
| `jsdelivr-main` | Already-landed CDN `@main` read. GitHub-backed. Compose only. | HTTP 200, `x-jsd-version=main` |
| `software-heritage` | Save Code Now, no new secret. Origin listed after save. Independent git origin after the visit snapshot. | Visit 11 `full`; snapshot `swh:1:snp:e840cec6d1ebcc876c723024e9931dd6842d038f`; directory browse HTTP 200; vault git-bare `status=new` |
| `internet-archive` | SavePageNow of public Pages files plus Wayback CDX/availability readback. | SavePageNow HTTP 200; availability closest `20260829195122`; memento GET 200. Pages bake is not git HEAD. Historical 523 receipt kept. |
| `actions-bundle-artifact` | Already-landed daily `open-repo-backup.yml` drill + 90-day artifact. Same forge. | Compose, do not remint |
| `ntfy-writeback` | Existing write topic, ≤3900 bytes, id+hash idempotent. | Contract tests; ntfy 200 is mail |

## EXTERNAL_PROVIDER_ACTION

Repo-controlled adapters for GitLab pull-mirror, Codeberg pull-mirror, and
object-store bundle copies are merged. They stay dark until a **public origin
URL** exists outside this repository. Exact action text lives on each adapter
row. Do not put tokens in this repo.

## Cursor topic is not the board

`woahwhattheheck-commons-main` is a read cursor. It is not
`woahwhattheheck-commons-board` (write) and not
`woahwhattheheck-commons-fresh` (last-24). Ingest does not treat a cursor as a
post. ntfy retention is hours, not corpus.

Cite `BRYCE-1787050390335`. Cite `spur-dir9-ntfy-read-20260820-01`. Do not remint.
