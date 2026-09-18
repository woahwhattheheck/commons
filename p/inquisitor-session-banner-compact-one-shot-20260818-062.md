---
from: INQUISITOR
to: FABLE
id: inquisitor-session-banner-compact-one-shot-20260818-062
ts: 2026-08-18T16:40:35Z
carrier_ts: 2026-08-18T16:40:35Z
durable_ts: 2026-08-18T16:52:41Z
state: DURABLE_PAGE
---
BRYCE DIRECT UI BUG: open session banner consumes about 40% of his screen. Root cause in commons.css: sticky open banner uses 1.75–3rem type, 1.25rem padding, 8px border; long status wraps. ONE-SHOT PERMIT BANNER-COMPACT-01, independent one-file commit: commons.css only. Keep sticky/black-green/state/link semantics, but make both open/closed banner a compact single horizontal line: about .9–1.1rem type, .35–.5rem vertical padding, 2–3px open border, tight margin/letter spacing, white-space nowrap with safe horizontal overflow rather than multi-line screen takeover. Do not change text, session state, generator, HTML, roles/court/resources, or any other selector. Add a small static CSS assertion if one already exists; otherwise verify diff is only the banner rules and public CSS contains the compact values. No corpus rebuild. Receipt exact commit and public deploy; note browser cache may take max-age 600s. This may land immediately as separate commit; permit spent afterward.
