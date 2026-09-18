# VCTC ERP + Grants Management pursuit carrier

Operation `VCTC-ERP-GMS-TEAMING-PURSUIT-ZMQV5R9-20260916` tracks the public Ventura County Transportation Commission 2026 ERP/GMS solicitation without pretending Token Junkie Labs is an ERP OEM or qualified prime.

The carrier is deliberately fail-closed. `official_sources.json` records all four buyer-controlled documents as **unretrieved** because this execution harness could read the official RFP through its PDF reader but could not obtain raw document bytes (the XLSX endpoints were rejected by the web reader and the container has no network resolution). Therefore the checked-in discovery fixture cannot reach proposal readiness. Exact raw bytes + SHA-256 must be recovered through an authorized source path and signed into a separate authority document before requirements or cost readiness can be asserted.

## States

- `HOLD_CONTROLLING_RFP_REQUIRED`
- `HOLD_CONTRACT_APPENDIX_REQUIRED`
- `HOLD_APPENDIX_BYTES_REQUIRED`
- `HOLD_DEADLINE_PASSED`
- `HOLD_REQUIREMENT_MATRIX_REQUIRED`
- `HOLD_MANDATORY_REQUIREMENT_GAPS`
- `HOLD_IMPLEMENTATION_EVIDENCE_PLAN`
- `HOLD_TEAM_QUALIFICATION`
- `READY_FOR_OWNER_PROPOSAL_REVIEW`

Even the strongest state is owner review only. The assessment hard-codes false authority for buyer contact, pre-proposal registration, questions, proposal submission, signature, pricing commitment, contract acceptance, insurance certification, production mutation, award/payment/revenue claims.

## Trusted-source boundary

Candidate packet source rows must exactly match a separately HMAC-authenticated `vctc-source-authority/v1` object. The key comes only from `VCTC_SOURCE_AUTHORITY_KEY_HEX`; candidate/source/assessment bytes cannot supply it. This is an integrity boundary for the locally retained official-source generation, not a claim that a hash establishes buyer authenticity by itself.

## CLI

```bash
export VCTC_SOURCE_AUTHORITY_KEY_HEX='<64+ hex chars>'
python -m opportunities.vctc_erp_gms_2026.cli sign-sources official_sources.json source_authority.json --key-id owner-2026-09
python -m opportunities.vctc_erp_gms_2026.cli compile example.discovery.json source_authority.json assessment.json --key-id owner-2026-09
python -m opportunities.vctc_erp_gms_2026.cli verify example.discovery.json source_authority.json assessment.json --key-id owner-2026-09
```

`sign-sources` is an owner/source-custody step. Do not sign guessed SHA values. Retrieve exact buyer bytes first.

## Commercial posture

The RFP permits ERP + qualified third-party GMS teaming / multiple awards. The truthful TJLabs lane is paid specialist implementation evidence: migration reconciliation, interface replay/idempotency, requirement→UAT traceability, exception/retest control and audit-ready cutover evidence. Product qualifications, public-sector references, OEM support, demo, insurance and physical submission belong to the qualified prime/vendor and must be independently evidenced.
