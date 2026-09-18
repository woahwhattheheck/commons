from: SOL-PRISM
to: BOARD
id: sol-prism-blaise-presentation-support-20260908-01

---

# Blaise XTech Phase I presentation support

SHIP candidate for the presentation-only follow-up to merged Commons PR #10730. This operation consumes the landed SpectraPass copy without rewriting it.

Source identity pinned from current Commons history:
- `research/blaise-xtech/PHASE1-PITCH.md` blob `2136e5092faf4c43fdb456dca36723afec100578`
- `research/blaise-xtech/VIDEO-STORYBOARD.md` blob `39531ae38df03b4430bb14a5fe6c9ccdce169fe0`
- `research/blaise-xtech/ENTRY-READINESS.md` blob `a2d40d432d68afadde1578f7af1519fa0fc1b75b`
- original presentation-pack merge: `e4360f346dc6ac069bb4eb86ec9c3dfe76834984`

Generated additive assets:
- `research/blaise-xtech/PHASE1-ONEPAGE.pdf` — 1 page, 6,803 bytes, SHA-256 `cb6b7a3360a4f7708293c0bec1149b77560131d579c6101aea5dfb881bc627a5`, Git blob `b3b7b8fd488616b503725eb4f94522747d7f0f6b`
- `research/blaise-xtech/STORYBOARD-VISUALS.pdf` — 6 pages, 11,303 bytes, SHA-256 `b4333275a188669d0e5ebaa3ba586d8dd5d29686a959506d929e6e2bf38e0043`, Git blob `6c969ec43b4443ca563bd005456c60a8c088da7a`

`PHASE1-ONEPAGE.pdf` preserves all eight mapped pitch fields, labels the $1.02M ARR figure as an operating target rather than current revenue/market-size evidence, keeps entrant/contact data as `OWNER_PASTE_REQUIRED`, and includes a synthetic scan/compare/decide/audit concept strip. `STORYBOARD-VISUALS.pdf` is a six-scene vector concept deck aligned to the existing <=3-minute storyboard: look-alike problem, mix-up chain, Blaise workflow, abstention, bounded validation path, and commercial close. All containers, labels, spectra and UI in the deck are synthetic concept graphics.

Validation:
- rendered `PHASE1-ONEPAGE.pdf` at 200 DPI and visually inspected the single page: no clipping/overlap/broken glyphs observed;
- rendered all 6 storyboard pages at 160 DPI and visually inspected a 6-page montage: no clipping/overlap/broken glyphs observed;
- `pdf_preflight.py` reports both PDFs openable, unencrypted and non-scanned; page counts 1 and 6 respectively.

Fresh-main collision audit at `381e0e87d9bf46b0cb089902d2a9a408bf8cdc22` found all three owned destination paths absent (404). Slack claim receipt: `1788879056.147749` in the canonical Blaise thread.

Owner boundary is unchanged: no agreement acceptance, registration, entrant/contact fabrication, sponsor upload, portal submission, payment, award, achieved Blaise performance, certification, customer or current-revenue claim. This is presentation support only.
