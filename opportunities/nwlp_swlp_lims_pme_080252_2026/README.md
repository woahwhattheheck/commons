# NWLP + SWLP Pathology IT LIMS preliminary market engagement

Internal commercial qualification carrier for Find a Tender notice **080252-2026** / OCID `ocds-h6vhtk-06ea51`, buyer **Imperial College Healthcare NHS Trust**, joint North West London Pathology + South West London Pathology market engagement.

## Current state

**`HOLD_QUESTIONNAIRE_REQUIRED`**.

The public notice/mirror identifies an estimated **£28m ex-VAT** future procurement, Atamis contract reference **C467704**, and a questionnaire response deadline of **1 October 2026 at 12:00 noon UK time**. The buyer questionnaire itself is not in this repository and was not recoverable from this harness without an authenticated Atamis session. That is a hard gate, not a documentation inconvenience.

This carrier cannot produce a READY state merely because somebody types a questionnaire digest into JSON: actual questionnaire bytes must be supplied to the CLI and must match the source ledger digest.

## What is here

- `sources.json` — source/provenance ledger and explicit questionnaire state.
- `requirements.md` — public-scope requirements/evidence matrix; questionnaire-controlled fields remain unknown.
- `route_matrix.md` — prime vs bounded teaming routes and their evidence gates.
- `questionnaire_recovery.md` — owner/authorized-operator recovery and source-binding procedure.
- `response_skeleton.md` — fill-only-after-recovery response structure; no invented answers.
- `partner_profile.md` — evidence-first profile for a clinical pathology LIMS prime and bounded specialist seams.
- `qualify.py` — deterministic, stdlib-only fail-closed evaluator.
- `fixtures/public_hold.json` — current truthful HOLD fixture.
- `tests/test_qualify.py` — hostile tests covering source binding, duplicate keys, bool/int aliases, authority escalation, questionnaire digesting and route readiness.

## Run the current fixture

```bash
python3 qualify.py fixtures/public_hold.json
```

Expected exit code is `3` and state is `HOLD_QUESTIONNAIRE_REQUIRED`.

A future authorized operator may recover the actual buyer questionnaire, update `sources.json` with its SHA-256 + reviewed state, update the manifest's source-ledger digest, and pass the questionnaire file with `--questionnaire`. The engine will still hold unless the selected route's capability evidence is proven. A teaming route also requires an evidence-backed prime partner confirmation.

## Exit codes

- `0` — `READY_FOR_OWNER_MARKET_ENGAGEMENT_REVIEW`; still **not buyer submission authority**.
- `3` — valid packet, fail-closed HOLD.
- `2` — invalid/unsafe input.

## Authority ceiling

This package authorizes no Atamis registration/login, buyer contact, questionnaire submission, supplier representation, NHS/UKAS/clinical certification claim, pricing or staffing commitment, contract acceptance, spend, or revenue claim. It is internal qualification only.
