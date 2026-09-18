# Instructions — CI-red fix recipe

1. Collect intake (`intake.md`): public repo URL, failing Actions run/job URL, red check name, branch/PR, contact email, the green definition.
2. Open the job log. Save the failing step command and the traceback. Classify with `python3 host/ci_fix_pack.py --classify-log <log> --json` (or the same `classify_log` helper).
3. Check out the exact failing SHA. Reproduce **the same command the job ran** locally. If you cannot reproduce, stop and say so — do not ship a guessed patch.
4. Apply the thinnest patch that makes that command green. Prefer one file. Do not redesign the matrix. Do not add a live workflow unless the buyer already owns that slot.
5. Re-run the command. Red then green must both be in the receipt.
6. Open a thin PR using `pr-body.md`. No secrets. No Autopsy. No invented Stripe.
7. Fill `receipt-skeleton.md`. Send the PR URL and receipt to the intake email.

Fence: public evidence only. Never Bryce-as-buyer. Tip KEEP. #8802 off.

Canary (this land’s sample): `python3 host/ci_fix_pack.py --canary --json` on `sample/fixture/` — unittest starts red, thin `health.py` patch, unittest greens.
