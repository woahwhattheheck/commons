# Offline multi-draft review reader

Generate one read-only HTML file from the existing parent compiler report and labeled analyst drafts. This presents `handoff_review.reconcile`; it does not introduce another assessment engine. Original source records, exact note text, draft dispositions, repeated content, disagreement, missing evidence and all twelve cells remain available. Matching content is not independent corroboration or acceptance.

## Generate and use the reader

From `revenue/uiowa_rfq_18649_workbench/` in a full Commons checkout:

```sh
python handoff_review.py example DEMO_INPUTS
python handoff_review_html.py DEMO_INPUTS/report.json \
  --handoff analyst-a DEMO_INPUTS/analyst-a.json \
  --handoff analyst-b DEMO_INPUTS/analyst-b.json \
  --classification SYNTHETIC_REHEARSAL --output REVIEW.html
```

Both output locations must be new. The generator never overwrites an existing file. The example uses the actual compiler's fictional inputs, not University observations or verified reviewer identities.

Open `REVIEW.html` in a browser that permits local file navigation. The generated document needs no server, account, model call, external asset, analytics or installation. All cells and exact notes remain readable with JavaScript disabled; scripts only add filtering and target navigation. Generation requires the existing Commons parent compiler, whereas opening the completed HTML does not.

For supplied operator drafts, select `--classification OPERATOR_DRAFT`. Classification is operator-declared, not verified provenance. The parent's non-authoritative mode is preserved; a draft is not a finding, approval, submission, signature or payment authorization.

## Review without losing the record

Select **Disagreement** to compare the synthetic ESS/security entries, which retain both `NEEDS_EVIDENCE` and `DISCUSS_WITH_PRIME` and their original notes. Expand the source record rather than treating the note as evidence. Use **Group** and text search to find an ID or phrase, then use the twelve-cell index. An indexed cell hidden by filters becomes visible and receives heading focus. Missing item identifiers are diagnosed rather than invented.

The historical synthetic example has two supplied labels, two distinct whole-draft contents, eleven pending cells and all twelve cells retained. Its overlapping reasons include disposition disagreement, incomplete review and note variation. Copies of a draft remain visible as separate labels but do not become independent corroboration or remove the original pending review.

**Download exact reconciliation JSON** returns the existing reconciler's canonical UTF-8 bytes plus a newline. It is not a newly scored or redacted dataset. Labels and their normalized-content digests remain available. Locators are displayed literally; only ordinary HTTP(S) locators are clickable, and no locator is fetched automatically.

Printing includes all twelve cells regardless of screen filtering. Notes and source references remain visible. Collapsed raw-JSON details are supplementary and print only when opened; the JSON download always retains the complete record. States are identified with words, not color alone. This is not screen-reader certification or a guarantee of pagination for arbitrary documents.

## Source lineage and recovery

Original renderer: **HELIOTROPE-K3Q7**, [PR #16399](https://github.com/woahwhattheheck/commons/pull/16399), commit `1d03cc0c89778c81f7976ec274a04836066ff25d`. The recovery retains the original renderer bytes exactly: Git blob `caf299ede29a02532708c49010b436dbfffe090b`.

Original reconciler: KESTREL-47. Duplicate-content correction: IBIS-93C. Parent vocabulary work: CADMIUM-R72F. Earlier parent replay: HELIOTROPE-58. The reader does not modify their engine, browser workbench, server, compiler or fixtures.

The required duplicate-import correction [#16318](https://github.com/woahwhattheheck/commons/pull/16318) merged on September 21, 2026 as `dcbd8ef69ad65e6d13b9d7624c3806362a3669ac`. At recovery base `48e070539232fdddf8bfa5aab7459b141ca400da`, `handoff_review.py` still has the original tested Git blob `b58c256db6745ae00367ce23ad62e80ab91d263f`. The former stacked-branch dependency is therefore resolved, not waiting for another peer-review or hosted-execution gate.

Recovery operation: `uiowa-handoff-html-k3q7-20260919`, seat `yz-fjord-73`. This delivery contains the working renderer and this guide only. Historical test suites, browser harnesses and root discovery wrappers are retained in the original PR's history, not restored to main or replaced by a new framework.

## What the existing execution record establishes

The original September 19 author record on #16399 reports 76 combined tests in normal and optimized Python, and 14 Chromium component cases in each mode, with zero skips. These are historical author results, not new recovery-seat execution or a fresh full-repository/hosted-CI pass.

The author also recorded an actual `net::ERR_BLOCKED_BY_ADMINISTRATOR` for native `file://` navigation. Its successful browser runs used in-memory component rendering, not a native file open. No administrator setting was changed. The renderer is standard-library-only; its historical browser harness is not a runtime dependency.

Local source evidence, browser behavior, hosted CI, deployment and University acceptance remain separate outcomes. No live University evidence, external contact, paid runner, scheduling or commercial authority is introduced by this delivery.
