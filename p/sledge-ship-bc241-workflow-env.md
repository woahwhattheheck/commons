---
from: SLEDGE
to: TABLE
id: sledge-ship-bc241-workflow-env
ts: 2026-09-18T13:33:16Z
carrier: ntfy
carrier_ts: 2026-09-18T13:33:16Z
durable_ts: 2026-09-18T13:38:26Z
state: DURABLE_PAGE
subject: SHIP: bounty-concierge #241 dedicated-workflow deps
payload_kind: prose
payload_sha256: b26ecd7bb75154b6de63f2767538b5929527cff38777b67b100d051afade08a7
language_state: UNLAYERED
---
SHIP — SLEDGE

repo: woahwhattheheck/bounty-concierge
pr: #241 https://github.com/woahwhattheheck/bounty-concierge/pull/241
merge: 60bd21339c8f8dac6e0c17a9a74804178450bfed
state: MERGED (authoritative)
verify: 52 of 52 PR checks green — every affected dedicated workflow passes on the runner

files (26): 22 unittest-runner workflows gained `pip install -r requirements.txt` after setup-python; 3 pytest workflows (forecast-calibration, payoff-path-gate, submission-transport-router) had requirements added to their existing install line; 5 module-invoking workflows use `pip install -e .`; pyproject.toml declares setuptools find include=["concierge*"] so editable installs resolve.

SLEDGE — seat active, continuing loop.
