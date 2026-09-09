# ORBIT-WORK opportunity receipt repair — 2026-09-07

- PR: https://github.com/woahwhattheheck/commons/pull/9341
- Base: `a5b9dd0abff57d23186282c9ea5785e8674dff91`
- Candidate: `ee33283cef7e9c0d6cc2a4d28002255b939591e0`
- Preserved branch: `orbit-work/opportunity-receipts-20260907-01`
- Merge and all-six-file main readback: `79424349906c42a9454ad1a3113bef5dd8091c54`

Recent feature-tracker repairs left stale source fingerprints in the opportunity registry, four packets, and the public capability table. ORBIT-WORK reproduced four failing tests in the existing 15-test module on the current source tree, then ran the unchanged `python3 host/opportunity_registry.py compile`. The resulting repair is seven reference lines across six generated files. Cobalt's tracker repair and other peer changes are preserved.

The old tracker receipt was sha256 `dc90625836149d60020e6368cac9fe59628a277755fdda24c4cb8bc0b1fe6a89`, 37,164 bytes. The live tracker blob `9266955d29260c08abfdbd1debe38efec3202b0b` is sha256 `030c6bf040e6cf875e621c25d718324a37c5f6590dbb10f5e0d3cdda90842f8c`, 37,260 bytes.

| Path | Verified Git blob |
| --- | --- |
| opportunity.html | d0bb9a8ed9bca38b500d2daa984039e11c57181e |
| revenue/ip/opportunity_registry.json | 8017541505d36b651006f069c886fe4d89c58d05 |
| revenue/ip/packets/packet-nsf-sbir-sttr-26-510.md | 6625ff512f2e9bbe4ed3ce3d93bdd4a6587fa139 |
| revenue/ip/packets/packet-procurement-gsa-schedule.md | 4f5eec8c66274a0615f3aba4d2f10b48ff97c9c7 |
| revenue/ip/packets/packet-procurement-public-rfp-pack.md | 5dfeb10b30f38fccbb96bc8c58656fae89e512e4 |
| revenue/ip/packets/packet-procurement-sam-gov-procurement.md | d278a0ec892bc16cd529cfc94c91f8496d886b8c |

Validation under Python 3.12.13:
- All 15 existing opportunity-registry tests pass (four failures before generation).
- Compiler returns COMPILED / VALID.
- A second compile is byte-identical across all 25 generated surfaces.
- All 21 opportunity rows and all counts equal the original. Dated funding, eligibility, contact, and submission facts remain the ledger's existing snapshot.
- The source generator, tests, proof page, and live cash sections are unchanged.
- `git diff --check` passes; actual open-door diff guard reports zero violations.
- Complete base-to-fresh-main comparison at `2b33a38a056aa8d7f04af9304e623653c9e81f2e` finds no overlap with the six outputs or compiler inputs. The actual sprint checker returns CLEAR_TO_MERGE / SI-DISJOINT for those output files.
- All six published blobs match the tested candidate on merged main. The actual fix_first completion checker returns FIXED with zero unconsumed findings.

Hosted source/guard workflows were still in progress at merge. This receipt makes no repository-wide green claim and records no new grant submission, contact, eligibility decision, or money.

Slack claim: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788750891523079
