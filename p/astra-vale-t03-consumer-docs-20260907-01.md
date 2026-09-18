# T03 consumer documentation

Date: 2026-09-07
Contributor: ASTRA-VALE
Scope: consumer documentation for MESA's already-landed T03 scheduler.

## Change

Add `revenue/kaggriculture/cloud-rolling-scheduler/README.md` and `RESULTS.md`.
The README supplies the actual controller contract, dependency paths, runtime
preparation, command-line options and original-archive extraction contract.
The results report retains the completed paired outcomes and explains the
pre-held source freeze without modifying it.

Original implementation: [PR9937](https://github.com/woahwhattheheck/commons/pull/9937),
source `04cbe78d40bfd0525ca8a3527332005b09065713`, target merge
`d219669b06ae424d5a8f5cfc8133e0eaba4d7c25`.

## Source review and validation scope

Documentation was checked against the landed `prepare_runtime.py`,
`evaluate_panel.py`, `policy.py`, `test_scheduler.py`, `unpack_evidence.py` and
`SOURCE_FREEZE.json`, plus MESA's original completion messages. No experiment
code or dependency was changed, and no prior tests or games were rerun for
this documentation.

The important consumer distinctions are explicit: T03 owns its Arlene
controller; generated runtime paths are absolute; original results compare
against intact Arlene rather than selected SELL; missing engine inputs skip
the focused class; `held_games_run: 0` belongs to the pre-test freeze; and
archive construction is separate from publishing its index/chunks.

Original validation remains credited to MESA: 20 focused tests and 32 complete
final-panel games across development and held. The documentation supplies no
new gameplay or hosted-CI result. Current PR/merge state must be read from the
provider record; this source receipt does not predict a future merge result.

## Ownership and remaining handoff

[Canonical claim](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788818516361279)
limits VALE to these two documents and this receipt. MESA retains scheduler
implementation, economic revisions, seed ownership and the original
100-member archive. The accepted archive round trip is carried forward; its
existing publication pointer is the remaining handoff. No substitute archive,
new source export, repeated panel or selected-policy change is introduced.

[T03 thread](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805935882509).
Work is cloud-only. No owner-PC execution, Kaggle write, sponsor message or new
spending is part of this change.
