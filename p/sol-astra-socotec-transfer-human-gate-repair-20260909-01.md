# SOCOTEC transfer + named-human gate repair

Operation: `socotec-transfer-human-gate-repair-20260909-01`
Date: 2026-09-09
Independent review blocker: PR #11224 review `5157921050`
Source baseline: source PR #11224 + expanded-fixture hardening PR #11231

## Defects consumed

1. The landed `allowed_transfer()` parsed only final numeric suffixes. A fabricated origin such as `FAKE-25` therefore matched the predecessor of `SOC-01`; with the deterministic ticket and legacy payload/hash recomputed over that fabricated string, the job could traverse the transfer gate as if the namespace were canonical.
2. The landed `named_human()` accepted any two non-reserved alphanumeric tokens of length >=2, including digit-only identities such as `12 34` and `1234 5678`.

## Repair

- Add canonical namespace parsing with full `SOC-XX` grammar and range `01..25`.
- Perform same-site/predecessor transfer arithmetic only after both namespaces pass canonical validation.
- Preserve the valid wrap transfer `SOC-25 -> SOC-01`.
- Require at least two alphabetic name tokens in addition to the existing reserved-automation-token and token-length checks.
- Add process-level regressions proving `FAKE-25`, `SOC-025`, `SOC-00`, `SOC-26`, and bare `25` remain `UNAUTHORIZED_TRANSFER` even when a matching deterministic ticket and legacy payload/hash are recomputed.
- Add release regressions for `12 34`, `1234 5678`, `Jordan 12`, and `1234 Rivera` while retaining `Jordan Rivera` as the positive control.
- Preserve PR #11231 expanded-fixture digest enforcement unchanged.

## Evidence

Fresh baseline blobs before this repair:
- source `320a0df7f909a945f3024ec9e410b38fb583c73e`
- test `e6e93056dd461b95ec157ac92df50e1996ba14d5`
- fixture `cce2ec3f671c9f7627f44ebc3bdb4a3a23331436`
- manifest `cf3908f8f7a95a349cd0e9ae9ff6623b0a6be15f`

Repaired Git blobs created before any ref mutation:
- source `0ebc884cd217e8615d3f6e98319af86697d037ba`
- test `14e463d06968c9e29a24d76c57615248f91a03a3`

Focused pre-publication predicate matrix: **PASS** — all 25 canonical same-site/predecessor relationships remain allowed; `SOC-25 -> SOC-01` remains allowed; malformed prefix/width/range origins above are denied; `Jordan Rivera` remains accepted; digit-only and one-alpha-token identities above are denied.

The full 12-test suite is not independently claimed from the local shell in this repair receipt. The prior #11231 baseline was reported 12/12 PASS; this repair is intentionally confined to the two predicates and focused regressions, and the exact PR diff plus any hosted checks are the publication evidence for integration.

## Boundary

Synthetic/read-only acceptance only. No live LIMS/QMS/scheduling/instrument/reporting/provider/customer system was contacted or mutated; no accreditation/compliance determination, external report release, outreach, spend, or owner-PC action occurred. Report release remains copy-only and `sent=false`; automatic release remains disabled.
