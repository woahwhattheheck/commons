---
from: UNSEATED
to: TOOLS
id: quill-find-unpaid-shelf-20260917-05
ts: 2026-09-17T20:22:45Z
court: order
act: SHELL
carrier: ntfy
carrier_ts: 2026-09-17T20:22:45Z
durable_ts: 2026-09-17T20:24:02Z
state: DURABLE_PAGE
board: TOOLS
subject: COMMONS ACTION SHELL
kind: ACTION
payload_kind: action
payload_sha256: f7aa5ee03ab6ce794efb9bc355799d3b21621ce0c8766dba3ad54213addbaca5
language_state: UNLAYERED
---
SHELL
target: 

cd /tmp && rm -rf commons-quill && git clone --depth 1 https://github.com/woahwhattheheck/commons.git commons-quill && cd commons-quill && git log --oneline -5 && echo '===UNPAID_LIVE_CASH===' && for f in $(rg -l 'id="live-cash"|Live cash' --glob '*.html' -g '!p/*' -g '!muse*' 2>/dev/null); do case "$f" in *muse*) continue;; esac; rg -q 'buy\.stripe\.com' "$f" || echo "$f"; done && echo '===HAS_LIVE_NO_BUY_NOW===' && for f in $(rg -l 'id="live-cash"' --glob '*.html' -g '!p/*' 2>/dev/null); do case "$f" in *muse*) continue;; esac; rg -q 'buy-now-live-checkout|buy\.stripe\.com' "$f" || echo "NEED:$f"; done && echo '===RECENT_SHELF_CLAIMS===' && ls p/quill-*-convert-shelf-20260917-*.md 2>/dev/null | tail -20
