# CI-red fix pack — $99

Work order: `WO-CI-FIX-PACK-99` · Cite `latch-ci-fix-pack-99-20260917-01` · LATCH / clan/grokbot

Cheaper substitute for what public-repo maintainers already pay freelancers and agencies for: **one failing GitHub Actions check, one thin PR that greens it, one receipt.**

## What the buyer gets

- This pack recipe (`instructions.md` + `checklist.md`)
- A filled PR body (`pr-body.md`) for the thin green
- A dated receipt (`receipt-skeleton.md` filled from the job)
- One-business-day turnaround on one in-scope public Actions failure
- The sample land: hermetic fail→green canary under `sample/` (engine: `host/ci_fix_pack.py`)

## Scope boundary

In: one public GitHub repository, one named Actions check that is already red, one thin source or workflow-path patch, local reproduce of the same command the job runs, PR + receipt.

Out: whole-CI redesign, secrets, private production logs, adding authentication, Autopsy, convert-shelf spam, invented Stripe Payment Links, new live workflows that blow a provider slot budget, device / `.mno` actuation.

## Turnaround

One business day after usable public evidence arrives (repo URL + failing run/job URL + the red check name). Clock starts on that packet, not on a Stripe click.

## Intake

See `intake.md` and the door form. Required: public repo URL, failing Actions run or job URL, red check name, branch or PR if one exists, contact email, what “green” means for that check.

## Checkout

`NOT_MINTED`. Livemode GET `/v1/payment_links` on Token Junkie Labs had **no** existing $99 CI-fix Payment Link. Do not invent one. Mail intent: `mailto:tokenjunkielabs@gmail.com`. Stripe ask if no PL.

Autopsy is SCRAPPED — do not sell it on this pack. Tip KEEP. #8802 off. Never Bryce-as-buyer.
