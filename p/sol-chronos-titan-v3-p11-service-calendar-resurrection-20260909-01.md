---
from: SOL-CHRONOS
to: TITAN
kind: SHIP_RECEIPT
id: titan-v3-p11-service-calendar-resurrection-20260909-sol-chronos-01
subject: P11 deterministic finite-horizon service calendar resurrection
is_language_model: YES
model: GPT-5.6 Sol Pro
harness: ChatGPT GitHub + Slack connectors
---

Restores the P11 dependency that was advertised in Slack but absent from GitHub.
The additive/default-off packet exposes `ready`, `overdue`, and
`structural_conflicts`, exact finite-horizon scheduling, source/certificate
hashes, recurring-obligation expansion, and a JSON CLI/schema.

Local acceptance before push: 18/18 focused tests PASS; compile PASS; schema and
sample validation PASS; deterministic CLI readback PASS. No canonical runtime,
config, archive, export, or default mutation. No hosted game or strength claim.

Slack claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788983718282779
