# Recover analyst work in the current tab

Reinspecting the same evidence now recovers its saved notes and dispositions.
Drafts stay bound to the complete report receipt and pass the existing draft
validator before restoration. The compiler report and every authority flag remain
unchanged.

## Working with one assessment

1. Inspect the candidate and evidence-authority JSON files.
2. Select a cell and enter a note or disposition. The draft is saved in this tab
   as you work. The **Drafts saved in this tab** panel shows its receipt and counts.
3. Inspect the same files again. If the compiler returns the same report receipt,
   all saved notes and dispositions are restored together. The status announces
   that restoration; it does not represent approval of the assessment.
4. Download the JSON before closing or reloading the tab. In a new tab, inspect
   the matching evidence, select that JSON under **Saved draft handoff JSON**, and
   choose **Restore matching draft**.

The full receipt must match. Similar filenames, the same organization, or an
apparently equivalent assessment do not establish a match. A changed report with
a new receipt needs its own notes. The draft must also match the complete set of
12 cells, compiler statuses, mode, aggregate state, and synthetic-demo identity.

## Switching evidence and recovering a prior draft

Inspecting different evidence starts a clean report. Prior work stays in
**Drafts saved in this tab**, where the selector identifies each draft by receipt,
note count, and reviewed-disposition count. Select a prior draft and choose
**Download saved draft JSON** to keep it, even when no report is active.

To resume that work in the current tab, inspect its original evidence again.
The matching draft restores automatically. **Restore matching tab draft** applies
only to a selected draft that matches the active inspected report; it cannot open
an old report or move notes onto a different receipt. This cache keeps the latest
saved draft for each receipt, not an undo history or multiple versions of a draft.

## Clear, failed inspections, and invalid notes

| Action or condition | Active report | Saved work |
| --- | --- | --- |
| Reinspect an exact matching receipt | Newly inspected report | Matching draft restores after complete validation |
| Inspect a different receipt | Newly inspected report, with empty notes | Prior draft remains downloadable and bound to its old receipt |
| Clear workbench | Removed; report exports and restore are disabled | Existing drafts remain in this tab |
| Failed evidence inspection | Removed; stale report cannot remain active | Prior valid draft remains downloadable for later recovery |
| Load the synthetic UI demo | Synthetic demo only | Real report drafts remain separate; an existing demo draft may restore |
| Delete an existing note or reset its disposition | Current report remains | Saved draft is updated, including an explicitly empty draft |
| Current draft cannot pass serialization/validation | Replacement is blocked; current work remains visible | Last valid saved version is retained |
| Reload or close the tab | Session ends | Tab-memory drafts are removed; previously downloaded files remain yours |

For an invalid note, correct the displayed problem before replacing or clearing
the active report. The existing 4,000 UTF-16-code-unit limit and scalar-text
validation still apply. A saved download represents the last valid saved draft;
it does not silently include an invalid edit that could not be saved.

## Data and authority boundaries

- Drafts are serialized in browser-tab memory, with no localStorage, database,
  network persistence, automatic disk write, or automatic eviction.
- The cache stores draft text and display counts, never a report object. A prior
  report must be inspected again before any matching draft can be restored.
- A replacement inspection invalidates the active generation before asynchronous
  reads. Late inspection responses and late draft reads cannot restore a cleared
  or superseded report. A draft load also rejects intervening note edits.
- Restoration validates the whole draft before replacing either note map.
  Unknown cells, altered statuses, authority flags, malformed text, and mismatched
  receipts cannot partially apply a draft.
- Notes remain `DRAFT_NON_AUTHORITATIVE`. Recovery is not analyst authentication,
  evidence approval, submission authority, a signature, or a payment decision.

Use downloaded drafts only in the agreed private engagement workspace. The
repository examples and acceptance fixtures are synthetic. This feature is a
local workbench capability, not a deployed service or a claim of hosted CI success.
