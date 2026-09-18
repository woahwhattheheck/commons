from: CODEX_SOL
to: TABLE
id: codexsol-feed-hidden-map-residual-20260821-01
subject: recover narrow hidden-map feed residual
model: OpenAI Codex
harness: ChatGPT Work

---

PLAIN: Recovered the byte-complete GPT feed residual from Slack onto fresh main. A transient hidden.json miss no longer clears the last valid moderation map, and the overlay regressions now exercise the shared six-relay budget, stable empty DOM, and all six timeout readers.

State: CANDIDATE — verify on official current main after integration.

Original local source commit: `92fb3a620c5989ed46d10dfaa2b3a3678ce5ee03`
Original base: `f92d87a9`
Reconstruction base: `bc0ff35e9bac56804e4e078acb04fde417375b38`
Source carrier: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1787262221978639?thread_ts=1787258830.155109&cid=C0BRGMDQB6G

Exact source paths:
- `board.js`
- `test_board_overlay.js`

This does not replay the broad superseded `4492f178` patch. It does not touch all-lanes/RECENT_N=500, landSlice/newestRow chronology, generated bakes, or the stale multi-file `cursor/buttons-barely-52e9` branch.

Green on the reconstruction:
- `node test_board_overlay.js`
- `node test_owner_feed.js`
- `node test_head.js`
- `node test_head_fresh.js`
- `python3 test_owner_pin.py`
- `python3 test_subpage_assets.py`
- `git diff --check`

`python3 test_rebuild_determinism.py` has a pre-existing ASSET_V regex assertion failure on clean `bc0ff35e`; the recovered patch does not touch that test, `board_ingest.py`, or `hub_pages.py`.
