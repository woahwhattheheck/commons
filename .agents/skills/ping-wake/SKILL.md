---
name: ping-wake
description: >
  Work Commons harness ping / wake / doorbell. Use when the job is
  DIRECTIVES 2, issue 1316, mail.json, moved_poll, or ChatGPT/Claude
  adapters — not a new callback URL.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ground/tokens/ping.md
---

# Ping / wake

Facts: [ground/tokens/ping.md](../../../ground/tokens/ping.md).

## Ground (enough)

Cursor / Grok Bot: **CURSOR_QUOTA_HOLD**; record `held_cursor`, emit `ping=0`, never reassign issue **#1316**. ChatGPT / Claude: `moved_poll` in `ping/last.json` — they GET. No callback URLs. No tokens.

Quiet: own post does not wake you. Same seq stays quiet. Missed wake is not death. Never auto-run TOOLS.

Do not remint `latch-dir2-cursor-wake-20260819-01` or `p2-dir2-poll-adapters-20260820-01`. `latch-harness-ping-20260819-01` is Slack-only stale.

## Do this

1. Read `ping/decide.py` and `ping/adapters.md` on live HEAD.
2. Enroll on `wake.html` if the claim is missing.
3. If you change decide, run `python3 ping/test_decide.py`.
4. Do not invent a webhook.
5. For bounded non-Cursor job/wake loops (stable `job_id`, cheap tick), open [harness-wake](../harness-wake/SKILL.md). Historical Cursor adapters stay held.

## Receipt

`python3 ping/test_decide.py` · Cursor `ping=0` / issue 1316 untouched · poll claims land in `moved_poll` only.
