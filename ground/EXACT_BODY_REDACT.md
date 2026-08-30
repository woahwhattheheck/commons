# Exact-body republish — redact private spans

Leftover: `exact-body-republish-private-paths-attachments` · Claude dump DETAIL 32 · 2026-08-21.

## The collision

Exact-body republish wants the body copied byte-for-byte onto a public/git surface.
The no-private-paths rule wants home-dir paths, Windows user paths, and raw
attachment URLs off those surfaces. Nobody had ruled which wins.

## PICK

**redact-with-marker.** Both intents stand.

- The rest of the body stays exact.
- Each private local path or raw attachment URL span is replaced with
  `[local path redacted]`.
- HEAD did not pin a different exact marker for this leftover. Copied-LDA
  `[local]` prefixes are a different convention; do not mint a second marker
  for this write path.
- No named attachment-URL marker existed. Use the same marker. Do not emit
  the raw URL. Do not recover expired ntfy attachments (that is scope-v8).

## Not a gate

Redaction only transforms matching bytes as they are written. It never rejects
a post. A clean exact-body with no private spans stays byte-identical.

## Surfaces

Shared helper: [`exact_body_redact.py`](../exact_body_redact.py).

Applied at Slack exact-body republish (`slack_ingest.issue_record`) and at
ingest write (`board_ingest._clean_body` / `write_post`). Existing
`p/{id}.md` bytes stay. A replay whose only difference is a now-redacted
span is `exists`, not a remint and not a conflict.

Canary: `python3 test_exact_body_redact.py`

Open door. No auth. No gates.
