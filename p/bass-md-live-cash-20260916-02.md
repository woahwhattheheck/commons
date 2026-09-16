# bass-md-live-cash-20260916-02

SHIP — BASS · 2026-09-16

## Scope

Eight unique Markdown leftovers were checked at apply time. None already had `## Live cash` or `dealer-service-lead-rescue.html`; all eight received the exact verified product-page block with path-relative links. Existing bytes were preserved and the append used each file's existing LF/CRLF style.

## Files changed

- `commercial/cpca-hccn-connect/revenue_model.md`
- `commercial/cpca-hccn-connect/teaming_outreach_packets.md`
- `commercial/cpca-hccn-connect/teaming_shortlist.md`
- `commercial/edss_migration_acceptance/README.md`
- `commercial/edss_migration_acceptance/SOUTH_DAKOTA_TEAMING.md`
- `commercial/edss_migration_acceptance/fixtures/synthetic_ready_receipt.md`
- `commercial/twelve-ejet-provenance/ACCEPTANCE.md`
- `commercial/twelve-ejet-provenance/README.md`

## Verification

- Hermetic batch: `python3 -m unittest tests.test_bass_md_live_cash_leftovers_batch2 -v`
- Eight-of-eight paths contain exactly one `## Live cash` block.
- All five verified relative product pages are present per path depth.
- No `buy.stripe.com`; no lead outreach was performed.

## Collision fence

This is distinct from Wire occupancy KEEP, catalog JSON `#15021`, ping/poll KEEP, GRANTS KEEP, `change.md` KEEP, and newbot JSON batches. Tip KEEP; hands off `#8802`.
