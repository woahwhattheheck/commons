# T03 complete-file result publication

The existing paired runner now publishes a result filename only after its JSON
bytes have been serialized, fully written, flushed and closed. This changes the
file-publication boundary in `evaluate_panel.py`, not the game, policy,
evaluation limits, pairing formulas or [resume identity](RESUME.md).

## Consumer behavior

Use the existing `evaluate_panel.py` CLI without new flags. Individual game
files are created with an exclusive atomic hard link from a same-directory
staging file. An overlapping writer cannot overwrite a completed cell.
`panel.json` is installed by same-directory atomic replacement: a failed write
leaves the previous complete summary unchanged. Short writes are completed
before either operation. The successful UTF-8 JSON representation is unchanged
on the tested Linux runtime.

On an exception or interruption, `.NAME.RANDOM.pending` files may remain beside
the reports. They are retained evidence, not published game records: they may
be empty, partial, complete, or an extra link to an already-published cell.
The exception includes the staging path where Python supports exception notes.
The existing reader never treats a pending file as a completed cache row.
Inspect and preserve these bytes; do not automatically rename them to game
filenames or manufacture an execution status from their presence.

A stop after cell installation but before summary replacement can leave a valid
older summary and newer complete cells. Resume with the same source and inputs;
the existing preflight checks those cells and reconstructs the summary without
replaying them. An exception during staging-link cleanup can also follow a
successful cell install, so check the actual final record instead of inferring
nonpublication from the exception alone.

The runner identity includes its own source hash. Earlier source-specific
results remain earlier results; do not relabel them to match this runner or
rerun completed experimental panels merely to update their metadata.

## Guarantees and limits

This is per-file atomic visibility, not a multi-file transaction, a job lock or
an exactly-once simulation guarantee. Concurrent callers can still compute the
same cell; one wins publication and the other retains its staged attempt.
Concurrent summary replacement is last-writer-wins, as before, but never exposes
partially written JSON. The filesystem must support same-directory hard links
and atomic replacement; there is no unsafe overwrite fallback.

The file is fsynced, but the containing directory is not. No power-loss
durability or recovery from an incomplete, unpublished attempt is claimed.
A killed process can leave staging files. Existing final data is never deleted
as part of recovering such an attempt.

## Reproduce the changed boundary

From the repository root in a disposable cloud environment:

```sh
python3 -B revenue/kaggriculture/cloud-rolling-scheduler/test_panel_publication.py -v
python3 -B revenue/kaggriculture/cloud-rolling-scheduler/test_panel_resume.py -v
```

The new suite runs 18 methods; the existing resume suite runs its unchanged 27.
Six new methods use Linux resource limits or SIGKILL and explicitly skip on
other systems. The tested environment was Python 3.13.5 on Linux. The production
runner and filesystem/process operations are real; `play()` is the existing
labelled evaluator fixture. There are no official-engine games, new game seeds,
policy-strength results or deadline changes in this delivery.

Exact predecessor: blob `d98ca4fdb78b25f24c7c1afc4686873dfd337ed0`, available in
[PR10031's merge](https://github.com/woahwhattheheck/commons/blob/5710685ea157cd91c669984421ede1b46872018e/revenue/kaggriculture/cloud-rolling-scheduler/evaluate_panel.py).
After materializing that existing source as `/tmp/t03-before.py`, run the same
four defect assertions:

```sh
T03_PANEL_PATH=/tmp/t03-before.py python3 -B \
  revenue/kaggriculture/cloud-rolling-scheduler/test_panel_publication.py -v \
  PublicationCases.test_file_limit_never_exposes_partial_cell \
  PublicationCases.test_file_limit_preserves_previous_summary \
  PublicationCases.test_kill_during_cell_write_keeps_final_absent \
  PublicationCases.test_kill_during_summary_write_preserves_old_complete_bytes
```

All four fail on the predecessor with zero test errors; they pass on the repair.
The original 8192-byte OS-limit witnesses retain invalid final JSON and loss of
the prior summary. The repair keeps those incomplete bytes under staging names
and preserves the prior final report. Additional cases cover short/zero writes,
fsync/link/replace errors, cancellation, cleanup after installation, recovery
without repeat play calls, and two competing real publishers.

[PUBLICATION-VALIDATION.json](PUBLICATION-VALIDATION.json) contains exact source
hashes, counts, log lengths/digests and the original OS-limit observations.
The full before/after packet `TITAN-VALE-T03-atomic-results.zip` retains the
original unencoded logs and predecessor source. Hosted checks, if any, are
separate from these local filesystem results.

Ownership: VALE's T03 publication boundary only. MESA's scheduler, source freeze,
original results and archive remain intact. Canonical TITAN builder/release,
shared evaluator, model-lab executor and profiling consumers are unchanged.
[Canonical task](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788843820847719).

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
