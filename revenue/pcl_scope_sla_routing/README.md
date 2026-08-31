# pcl-scope-sla-routing-lims-01

Post-Acquisition Scope-Controlled Sterile-Package Study Routing + SLA Evidence for **Packaging Compliance Labs / Ryan Ott**.

Exact posted buyer fixture. Not a generalization. Not a core replacement.

## Boundary

Synthetic / mocked read-only. LIMS, instruments, scheduling, billing, and delivery simulated. No production writes. No PHI. `cash_usd=0`. STATE remains **HOLD / BUILD-AND-VERIFY**. Named human must act before report release. No automatic release.

Cite, do not remint: `canyon-multisite-regulated-intake-lims-01` (Adam, in flight), `made-scientific-princeton-rapid-qc-lims-01` (blob `e9469ada` PR 6720), `weck-coc-preaccession-validator-lims-01` (blob `3e837ad3`), `kincell-rtp-qc-release-bridge-lims-01` (blob `ac87ae7b`), `organabio-multisite-donor-coa-lims-01` (blob `8edbf578`), `elevatebio-pittsburgh-replication-lims-01` (blob `0f9048a9`), `roslinct-hopkinton-paperless-qc-lims-01`, SKUs 1–7, Billings Bid 1421, PR 6206.

## Fixture command

```bash
python3 revenue/pcl_scope_sla_routing/runner.py
python3 -m unittest test_pcl_scope_sla_routing.py
```

## Expected vs actual

| Check | Expected | Actual |
| --- | ---: | ---: |
| orders | 180 | 180 |
| valid | 150 | 150 |
| blocked | 30 | 30 |
| integrity / aging / distribution / product | 40 / 40 / 40 / 30 | 40 / 40 / 40 / 30 |
| incomplete / outside site scope | 15 / 15 | 15 / 15 |
| routed to exact facility / revision / sequence | 150 | 150 |
| blocked with expected reason | 30 | 30 |
| custody complete | 150 | 150 |
| 24-hour dock-to-start exact | 150 | 150 |
| 48-hour report exact | 150 | 150 |
| released without named QA | 0 | 0 |
| released after named QA | 150 | 150 |
| blocked released | 0 | 0 |
| replay changed records | 0 | 0 |

## Golden hashes

- `audit_sha256` `3715a8eb8fa2e15309467c94dc23ffc8977b5c8737d1aeb3daf7e1650cdcbd6e`

Replay of the entire 180-order corpus changes zero records and reprints the same audit hash.

## Files

- `fixture.json` — exact 180/150/30 contract
- `runner.py` — official binary
- `source.json` — leftover provenance
- `../../test_pcl_scope_sla_routing.py` — focused unittest
- `../../pcl-scope-sla-routing-lims.html` — login-free door
- `../../p/pcl-scope-sla-routing-lims-01.md` — leftover receipt
