# action-pad-ordinary-path-regression-20260831-01

Status: CANDIDATE
Date: 2026-08-31
Base: `329ec51e89120ce0cb50667bc2a45c17f35d9e2a`

## Measured defect

Hosted broad battery [33351478796](https://github.com/woahwhattheheck/commons/actions/runs/33351478796) failed `test_action_pad_zero_auth.py` because the test still required an ordinary Windows path to be replaced by `[local path redacted]`. Current `exact_body_redact.py` intentionally preserves ordinary local paths byte-for-byte and redacts only raw private attachment-download URLs.

## Repair

- The ordinary-path case now asserts exact preservation.
- A separate private Slack attachment URL case asserts marker replacement and URL removal.
- No production writer, admission behavior, authentication, identity, approval, or permission logic changed.

## Truth boundary

This is a test-contract repair. It does not claim buyer delivery, outreach, payment, settlement, payout, or cash. No Grok submission, retry, queue, or spend occurred.
