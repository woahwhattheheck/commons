# Enveda CASMI 2026 — molecule ID from mass spectra

Isolated public-fact qualification carrier for the live Kaggle competition
`enveda-CASMI26-molecule-id-mass-spectra`. Default decision is
`HOLD_KAGGLE_TERMS_UNACCEPTED`.

## Public facts

- Organizer: Enveda (CASMI founders Emma Schymanski and Steffen Neumann supporting)
- Title: Enveda CASMI 2026 - Molecule ID From Mass Spectra
- Host: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra
- Opened: 2026-09-14
- Closes: 2026-12-14
- Prize pool (public fact, not cash): $50,000 total / $16,000 first
- Public contact: casmi-2026@enveda.com
- Gmail classify: Kaggle launch mail to tokenjunkielabs@gmail.com 2026-09-16, not buyer interest

## What this proves

`casmi_2026.py` source-binds those public facts and compiles a buyer-neutral
spectrum parse demo. The demo is labeled `DEMO_CAPABILITY` and cannot satisfy
an unknown mandatory evaluation metric or become a Kaggle submission.

Qualification stays HOLD until exact owner evidence records:

1. `kaggle_terms_accepted` is JSON true
2. nonempty `owner_team_name`
3. `owner_submission_authorized` is JSON true

Even then the packet is `INTERNAL_READY_NOT_SUBMITTED`. Authority fields for
join/submit/contact/prize/cash/revenue remain false.

## Authority

No Kaggle account mutation, no submission, no organizer contact, no prize
claim, no payment, no revenue. Do not swarm-reply the launch mail.

## Checks

```bash
python -m py_compile casmi_2026.py test_casmi_2026.py
python -m unittest -v test_casmi_2026.py
python -O -m unittest -v test_casmi_2026.py
python casmi_2026.py --qualify
```
