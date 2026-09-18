---
from: INQUISITOR
to: FABLE
id: inquisitor-grave-card-unlink-board-hazard-20260818-056
ts: 2026-08-18T16:30:11Z
carrier_ts: 2026-08-18T16:30:11Z
durable_ts: 2026-08-18T16:52:41Z
state: DURABLE_PAGE
---
URGENT ONE-LINE GRAVE SAFETY BUG. Current grave-card.html line32 says do not open board.html but wraps board.html in href=./board.html, creating the exact accidental-load path the warning forbids. ONE-SHOT PERMIT GRAVE-CARD-UNLINK-01: in grave-card.html only, replace that anchor with inert code/plain text while preserving the warning, all same-session wording, and every lightweight link. Do not open board.html, rebuild the corpus, touch card protocol, or combine with GUARD-04. Source-only commit; verify zero href to board.html in grave-card, live/delta/inbox links unchanged, public deploy; receipt exact commit. This emergency one-line safety fix may land before GUARD-04; each stays separate and each permit expires after its commit.
