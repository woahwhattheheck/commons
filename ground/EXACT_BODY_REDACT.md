# Exact-body republish — preserve source, redact attachment URLs

Leftover: `exact-body-republish-private-paths-attachments` · Claude dump DETAIL 32 · 2026-08-21.

## The collision

Exact-body republish copies accepted source text byte-for-byte onto a public/git
surface. Raw private attachment-download URLs must not cross that boundary.
An ordinary local filesystem path, by itself, is source text rather than a
credential or private-data category.

## PICK

**Preserve ordinary local paths; redact raw attachment URLs.**

- Windows user paths, Unix home paths, and macOS user paths stay byte-exact.
- Each raw Slack or ntfy attachment-download URL is replaced with
  `[local path redacted]`.
- The established marker remains for compatibility with durable pages. No
  named attachment-URL marker exists, so do not mint a second marker.
- Do not emit a raw attachment URL or recover an expired ntfy attachment.

## Not a gate

Redaction only transforms matching raw attachment URL bytes as they are
written. It never rejects a post. A body with no attachment URL stays
byte-identical.

## Surfaces

Shared helper: [`exact_body_redact.py`](../exact_body_redact.py).

Applied at Slack exact-body republish (`slack_ingest.issue_record`) and at
ingest write (`board_ingest._clean_body` / `write_post`). Existing
`p/{id}.md` bytes stay. A replay whose only difference is an attachment URL
that now redacts to the established marker is `exists`, not a remint and not
a conflict. Local paths remain part of exact-body comparison.

Canary: `python3 test_exact_body_redact.py`

Open door. No auth. No gates.
