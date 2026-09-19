# White Box hour — delivery runbook

Cite [sku-whitebox-hour-20260826](./sku-whitebox-hour-20260826.md). Do not remint it.
Product sold: one dated White Box / dests hour, $250.
Buyer is owed `land/session-YYYYMMDD.md`: dests, receipts, what ran. Public file.

## 0. Trigger — confirm, don't assume

A completed Stripe checkout session is the only start signal. A click, a Slack
"sold", or a forwarded screenshot is intent only.

- TYPE-capable seat reads livemode: GET /v1/payment_links/plink_1U8lgGATH4EDE7XDlrVYTWhu
  plus the checkout session / payment intent for the buyer's email.
- Record in the session file: confirmation read time (UTC) and session/payment id.
- No confirmed payment -> do not start. Park and flag the sale thread.

## 1. Intake

- Send the buyer [the intake form](./whitebox-hour-intake-form-20260917.md)
  (or fill it from the sale thread).
- Missing fields that gate dests -> ask once, then proceed on paid scope only.

## 2. Schedule

- One dated hour. Commit date + window + timezone in writing before work.
- A slip is announced before the window, not after.

## 3. Declare dests

- Before the clock: write dests into the session file. Dests are what the hour
  targets — buyer-approved scope in buyer words, trimmed to fit 60 minutes.
- Out-of-scope discovered mid-hour -> park it, note it, keep delivering the
  paid dests.

## 4. Execute

- Keep receipts live: commands, diffs, SHAs, URLs, timings.
- Whatever the hour produces goes in the session file — partial included.

## 5. Session file

- Copy [the template](./whitebox-hour-session-template-20260917.md) to
  `land/session-YYYYMMDD.md`, fill every section, land on main.
- The public file IS the deliverable. HTTP is not the computer.

## 6. Notify

- Send the session-file link through the channel the sale came through.
- A fresh external thread is Muse-gated first.

## 7. Close

- Receipt line in the WO thread: buyer ref, session file URL, outcome word
  (DELIVERED / PARTIAL / BLOCKED), payment id.
- Renewal pointer: next hour is the same checkout. No discount, no free follow-up.

## Kill conditions

- Payment not confirmed -> no start.
- Scope doubles mid-hour -> finish paid dests, park the rest, say so in the file.
- Buyer unreachable after payment -> deliver the hour against the intake dests
  anyway, mark buyer-silent in the file, flag Bryce.
