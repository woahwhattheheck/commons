# Linden Housing Authority RFP 26-07 — owner review packet

Internal qualification carrier only. Source custody remains **Z-SteinhausMoraine-2315-Q4V8**. Recovery/finalization lane: **Z-Sol-Cascade-0119**. Canonical issue: https://github.com/woahwhattheheck/commons/issues/14261

## Bound public-notice facts

- Procuring entity: Housing Authority of the City of Linden (NJ)
- Solicitation: RFP **26-07** — AI Automation, Resident Communication & Operational Support Services
- Public notice posted: 2026-09-11
- Questions: 2026-09-21 15:30 ET
- Proposals: 2026-10-09 14:30 ET
- Submission channel: Housing Agency eProcurement Marketplace only; hard copy not allowed
- Published agency contact name on the notice: Dr. Marlena Berghammer, Executive Director

Public notice metadata is **not** the controlling RFP/addenda package.

## Fail-closed gates

The compiler refuses submission, pricing commitment, buyer email, portal registration, credential invention, award, payment, and revenue claims. Those flags stay hard-false even when an owner packet is internally complete.

Until the official package is acquired and hashed:

- evaluation weights stay `null`
- required forms stay `null`
- addenda stay `null`
- posture stays `HOLD_CONTROLLING_PACKAGE` or `HOLD_OWNER_EVIDENCE`
- blockers include `CONTROLLING_PACKAGE_NOT_BOUND`, `EVALUATION_REGISTER_UNKNOWN`, `FORM_REGISTER_UNKNOWN`, `ADDENDA_REGISTER_UNKNOWN`

## Acquisition checklist (owner + Muse gated)

1. Use an already-authorized private session on Housing Agency Marketplace if one exists. Do not register a new vendor account from this carrier.
2. Download the controlling RFP plus every addendum.
3. Hash exact bytes and bind them into `controlling_package.sha256`.
4. Rebuild the requirement / evaluation / form register from those bytes only.
5. Re-run `compile_packet` against current main.

No buyer mutation is authorized by this recovery.
