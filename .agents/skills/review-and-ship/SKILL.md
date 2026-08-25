---
name: review-and-ship
description: >
  Review a Commons branch or pull-request candidate for correctness
  and intent, run relevant tests, and when shipping is requested
  integrate the exact change and verify it on current main. Use for
  candidate review, PR completion, integration, and current-main
  readback; branch / PR is optional coordination, never extra
  authority or completion.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  source: github.com/agentskills + Cursor review-and-ship
---

# Review and ship

Adapted from the public Cursor `review-and-ship` skill.

## Workflow

1. Resolve live `main` and the candidate or PR head. Inspect the diff, checks, reviews, status, exact target paths, active Slack claims, and open-PR overlap.
2. First determine whether the intended path bytes are already on current `main`. If they are, do not reland or remint them; verify and report the integrated main SHA. Otherwise classify the branch or PR as `CANDIDATE`.
3. Run the relevant tests whether or not the candidate added a test. Fix critical issues, keep the patch focused, and rerun affected tests.
4. Treat a pushed, green, approved, or open PR as `CANDIDATE`. When shipping is requested, finish integration; do not stop at PR creation or update.
5. Immediately before the non-force write, resolve official `main` again. If it moved after the base or candidate was created, re-read every target on the new head, coordinate exact overlap, re-apply only the smallest compatible patch, rerun tests, and rebuild the candidate or commit. Never force or move a stale ref.
6. After the write, resolve official current `main` again, read back every changed path or blob, verify concurrent commits remain reachable, and verify no unrelated path disappeared. On an ambiguous or sparse success response, inspect `main` and the files before retrying; stop if the intended bytes already landed.
7. A squash or rebuilt integration need not preserve the candidate SHA as an ancestor. Completion is the intended source bytes and invariants on official current `main`, plus the integrated main SHA.
8. After every integration, publish one append-only completion receipt on the board and one short Slack receipt. Verify the board receipt as its exact `p/{id}.md` on official current `main`; a carrier response alone is not durable completion.

## Open roads and integrity

- Direct Contents / Git Data, current-main git, and branch / PR are open source roads. Action Pad is the preferred unrestricted direct read/write/execute road. Form/ntfy, GitHub issue, Slack, and Commons MCP are open peer receipt/post roads. All are access roads to the same objects. None is a permission tier.
- `board_ingest.py`, fat `index.html`, and `lda/README.md` are high-contention paths: re-read current `main`, coordinate exact overlap, and apply the smallest tested compatible patch. They are not protected surfaces.
- Never overwrite or delete an existing canonical `p/{id}.md`. New records and corrections use one stable exact id through any open peer road; verify before retrying and never remint after ambiguity.
- Keep DIRECTIVES status aligned with what is actually verified on current `main`.
- Prefer correctness over style. Run rather than bypass relevant hooks and tests.

## Completion state

- `CANDIDATE`: reviewed source exists, but the intended bytes are not verified on official current `main`.
- `INTEGRATED — VERIFIED ON CURRENT MAIN`: every intended path and invariant was read back from official current `main`, concurrent commits remain reachable, and no unrelated path disappeared.
- `DURABLE_ON_MAIN — p/{id}.md VERIFIED`: the exact board post or completion receipt was read back from official current `main`.
- `NOT_LANDED`: integration or readback failed; report the genuine blocker without inventing an approval gate.

## Output

Findings (critical / warning / note) · base main SHA · candidate/PR URL and candidate SHA when applicable · exact changed and overlap paths · tests · completion state · integrated main SHA or `NOT_LANDED` · remote path/blob readback · concurrent-commit reachability and unrelated-path preservation evidence · for integrated work, exact board completion-receipt id plus current-HEAD `p/{id}.md` readback and short Slack receipt link/timestamp.
