# Grok automation harvest — integrated readback — 2026-09-01

Status: **INTEGRATED — VERIFIED ON CURRENT MAIN**

Owner observation: triggered Grok automations continued firing for days while the interactive Grok.com account showed no remaining tokens. The durable task was to collect the produced work without guessing whether the behavior is a feature, a bug, or which quota pool paid for it.

## Observed automation surface

The operator-provided Grok Automations screen showed 14 visible automations:

- one daily automation;
- seven matching-event automations;
- six hourly automations.

The observed manifest is operator evidence, not a live Grok API census. Missing live state remains `UNMEASURED`; it is never converted into a fake zero.

## Harvest product

PR: [#7014](https://github.com/woahwhattheheck/commons/pull/7014)

Merge commit: `1ad1522021de64ce44068c644114ccdabb588a27`

Exact current-main blobs:

- `ground/GROK_AUTOMATION_HARVEST.md` → `f9a7e98e2b5a0a2688533f8fe584cf95ca38e455`
- `host/grok_automation_harvest.py` → `43271cfe8258defab00182193188dc9ece8b5cf4`
- `test_grok_automation_harvest.py` → `9e6fab6555025d4c72cb72d53942793706bb19c9`

The collector joins exact branch truth with canonical `p/*.md` receipt blobs at one frozen main SHA plus an optional operator-observed automation manifest. It does not fetch, checkout, merge, push, move refs, delete, or mutate accounts.

## Frozen harvest result

Frozen source main: `638bafb8732309850132e25582b7e950e3cfd52e`

- 391 measured branches: 355 `ANCESTRAL`, seven `LANDED`, 29 `UNIQUE`.
- 362 branches are Git-accounted; 29 remain explicit review rows.
- The review set is 22 old Grok heads plus seven active ChartTrace lanes; no blind merge occurred.
- 563 canonical Markdown receipts were measured.
- Provenance: 366 `EXPLICIT_GROK_COM`, 149 `EXPLICIT_GROK`, 26 `MIXED_EXPLICIT`, 16 `GROK_NAMED_ONLY`, six `EXPLICIT_OTHER_HARNESS`.
- Multi-label work tags include 265 PR-lifecycle, 65 repair, 53 Slack/Discord, 19 CI-watchdog, seven revenue, four Muhlnickel, three Pixel, two Titan Android, and one ChartTrace receipt.

The filename is only a discovery hint. Provenance comes from receipt header metadata, and body lookalikes do not change attribution.

## Verification repair consumed

The hosted battery for #7014 exposed stale resource-ledger assertions introduced by the already-landed toolset activation. That defect was repaired rather than left as a report.

Repair PR: [#7022](https://github.com/woahwhattheheck/commons/pull/7022)

Integrated main: `d6bbf5956acb2ed3900799aa98b61dc09ef9353b`

- `test_resource_ledger.py` → `5e4cbb80afc11002e5b8c4deb775ea26b97b0faa`
- 21/21 resource-ledger tests passed.
- 10/10 adjacent tool-consumption tests passed.
- Python compile and diff checks passed.
- Hosted source-parses, open-door, local-compute, Muhlnickel-spec, and path-manifest guards passed.
- The whole battery read back `test_resource_ledger.py` as PASS. Its remaining failure was confined to five pre-existing opportunity-registry projection assertions and did not touch the repair path.
- `fix_first.py` returned `FIXED` with zero report-only sessions and zero unconsumed findings.

## Recursive verification-loop warning

The owner identified recursive verification as a real failure mode: evaluators can begin evaluating one another until the system optimizes for proof production instead of repair and delivery.

The bounded fixer rule was posted and read back on the active repair surfaces:

- [#commons](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788269176091769)
- [#delegations](https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1788269177127629)
- [#build-demand](https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1788269176563649)
- [#cursor-master-updates](https://tokenjunkielabs.slack.com/archives/C0BTYUYNJJZ/p1788269177565259)

Freeze one claim, base/head range, and acceptance contract; verify once; repair the smallest compatible defect; perform one terminal readback; stop unless target bytes, evidence, or the explicit contract changes.

## Boundaries

Grok.com was not retried after Cloudflare blocked the authenticated browser route. No Grok token, automation, account, Slack history, Git history, branch, active ChartTrace lane, deployment, outreach, spend, payment, revenue, or Titan surface was mutated by the harvester. This receipt does not claim that the continued executions were a feature or a bug, and it does not infer which quota pool funded them.
