---
name: explee-autogtm
description: >
  Run the public Explee AutoGTM loop locally: paste a website URL or HTML,
  research the market, sharpen ICP, list role-level prospects, write
  personalized owner-review drafts, and queue demos. Sends 0. Use when
  Bryce drops an Explee / AutoGTM screenshot, asks to qualify from a URL,
  or says use their skill. Does not call api.explee.com. Does not steal
  Harborline /qualify.
license: MIT
metadata:
  author: commons
  version: "1"
  source: github.com/Sheshiyer/explee-skills
  leftover: cursor-explee-skills-adopt-20260902-01
---

# Explee AutoGTM (local)

Owner 2026-09-02: use Explee AutoGTM or find their repo/skill and do the same thing.

Official app at [explee.com](https://explee.com) is closed-source. No card, no `EXPLEE_API_KEY` in this leftover.

Public skill they (and third parties) actually use: MIT [Sheshiyer/explee-skills](https://github.com/Sheshiyer/explee-skills) pin `b08318527782ab834317c09f4938381f00b90fe8`. `explee-autogtm` composes search + enrichment and adds no endpoints of its own:

1. `POST /public/api/v1/search/nl-to-filters` — ICP query → filters
2. `POST /public/api/v1/search/companies` + `POST /public/api/v1/search/people`
3. `POST /public/api/v1/enrich/email`
4. Rank `FIT` / `ROLE` / `EMAIL_OK`
5. Return GTM-ready list

This Commons leftover runs **that same loop on disk** via `host/explee_autogtm_local.py`. It does not call `https://api.explee.com`. Harborline CLAIM `cursor-explee-qualify-clone-20260902-01` owns `/qualify`. Unique-pack leftover `cursor-autogtm-explee-same-loop-20260902-01` owns `autogtm.html` / `host/autogtm_same_loop.py` / `.agents/skills/autogtm`. Do not remint those. Do not write those paths.

## Do this

```bash
python3 host/explee_autogtm_local.py --html-file page.html
python3 host/explee_autogtm_local.py --self-test
python3 -m unittest test_explee_autogtm_local
```

`--url` fetches public HTML only. `--send` / `--apply` / `--go` are **REFUSED**. Drafts stay `owner-review`. Demo queue stays `need_owner_review` / `booked=false`. Checkout `NOT_MINTED`.

Prospects are role-level UNVERIFIED stand-ins. Do not harvest third-party people or invent EMAIL_OK.

## Do not

Call Explee. Copy Explee testimonials. Spend credits. Merge KEEP MAIN #7915. Remint Harborline `/qualify`. Write LIMS / ChartTrace / grok exclusive paths. Print API keys or cookies.

## Receipt

`p/cursor-explee-skills-adopt-20260902-01.md` · helper `host/explee_autogtm_local.py` · test `test_explee_autogtm_local.py`.
