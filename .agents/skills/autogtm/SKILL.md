---
name: autogtm
description: >
  Run the same AutoGTM loop Explee shows on explee.com (paste a website,
  research, sharpen ICP, find people, draft personal email, stage booking)
  and the same eight steps as the open-source twin cmn-labs/autogtm. Use when
  Bryce or a player says use Explee, AutoGTM, qualify clients while you sleep,
  or "find their repo/skill and do the exact same thing."
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ground/tokens/autogtm.md
---

# AutoGTM same loop

Facts: [ground/tokens/autogtm.md](../../../ground/tokens/autogtm.md).
Door: [autogtm.html](../../../autogtm.html).
Engine: [host/autogtm_same_loop.py](../../../host/autogtm_same_loop.py).
Existing compose: [website-people-email-book.html](../../../website-people-email-book.html).

Bryce 2026-09-02 `1788376550.004339`: use this (Explee screenshot) or find their repo/skill and do the exact same thing.

## Do this

1. Name the public mechanism: paste website → ICP → people → personal email → replies/book.
2. Name the open twin: [cmn-labs/autogtm](https://github.com/cmn-labs/autogtm) eight steps. Cite, do not copy AGPL source.
3. Run `python3 host/autogtm_same_loop.py --json` (fixture) or `--url https://…`.
4. Compose `host/website_people_email_book.py#extract_website` for ICP/offer plus the Smart Outreach catalog. Do not remint those ids.
5. Probe Explee `GET /public/api/v1/autogtm/projects`. 401 Missing API key is FINDER-FAILED, never a Commons lock, never silent 0. A private `EXPLEE_API_KEY` is agent-side credential work; never paste it onto Commons.
6. Keep send/book/cash at staged zeros until an owner mailbox/calendar exists.

## Do not

Add login to the door. Invent buyers, sent mail, booked demos, or cash. Remint `website-people-email-book-20260830-01`. Copy `cmn-labs/autogtm` source. Treat `--autopilot` as a send. Treat Slack-search miss as CLEAR.

## Receipt

`python3 -m unittest test_autogtm_same_loop.py` green. `p/{id}.md` on current main names the unique paths and the Explee 401 measurement.
