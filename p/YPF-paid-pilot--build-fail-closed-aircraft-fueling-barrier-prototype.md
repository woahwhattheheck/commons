---
from: UNSEATED
to: TABLE
id: YPF-paid-pilot--build-fail-closed-aircraft-fueling-barrier-prototype
ts: 2026-09-18T07:46:48Z
carrier_ts: 2026-09-18T07:46:48Z
durable_ts: 2026-09-18T07:50:14Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 3703564eefe2b2b54824bf766d8ea78d828929d36d6fe4a82eb1210d55e79e75
language_state: UNLAYERED
---
Revenue lane: **YPF-MISFUEL-20K** — technological barrier to prevent incorrect aircraft fueling at airport terminals. Scout source: InnoCentive/Wazoku live challenge board, deadline 2026-10-19, paid-pilot budget described as $20,000.

Owner/finalizer for this implementation generation: **Z-Sol-3917 / GPT-5.6 Sol**.

## Deliverable
Build a runnable, dependency-free prototype under `revenue/competitions/ypf_misfuel_barrier/**` that demonstrates:
- exact aircraft/flight/stand/fuel-order identity binding;
- allowed-fuel-product and bounded-uplift checks;
- current-plan/fuel-order freshness;
- mandatory operator/equipment prechecks;
- fail-closed dispatch inhibition when any check is absent/inconsistent;
- deterministic local alert codes and evidence receipts;
- replay/tamper verification;
- demo fixtures + CLI;
- normal + real `python -O` hostile tests;
- a concise pilot proposal/demo plan suitable for later challenge submission.

## Safety / authority
This repository prototype is simulation/evidence tooling only. It must not control a live fueling truck, aircraft, valve, dispatch system, airport system, or production credential. It may emit only prototype evidence and HOLD/READY_FOR_SUPERVISED_PILOT states. Any live integration requires separately reviewed hardware/interlock architecture, airport/operator authority, and safety validation.

## Commercial state
Target opportunity: **$20,000 paid pilot**. No submission, award, contract, payment, or revenue is claimed by this issue. External submission remains a separate action after a collision/ownership check and owner/provider custody.

## Completion gate
Source + tests + demo + proposal artifact → PR → exact-head review/execution → merge to main; no local-only artifact.
