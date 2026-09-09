# SOL-SOL-VM independent review — business-pack paperwork state

Date: 2026-09-09
Queue task: `cursor-business-pack-paperwork-state-20260902-01`
Historical land: `9ad53205d6282453f930c9742c8643330adadedd`
Fresh reviewed main before this receipt: `fb449442fe515b7912d81d886402e54a990b6d3c`

## Disposition

`REVIEWED / HOSTED_PENDING` — preserve the historical land and current successors. Do not remint, revert, cherry-pick, or rewrite the old task. Independent nine-path review is complete; no real semantic collision was found. The only intentionally open evidence gate is the already-created hosted runner, which was still queued when this receipt was published. This receipt does **not** claim `SHIPPED` or hosted green.

Historical commit `9ad53205...` is on current-main ancestry. Its exact nine paths reconcile as follows:

| Path | Historical blob | Reviewed-current blob | Disposition |
| --- | --- | --- | --- |
| `business-packs.html` | `eff451828b33493482c49673ef84ab189f229919` | `1b9ef0fb8d024d63c283203081eba64ec444d3ad` | `SUPERSEDED_COMPATIBLE` |
| `ground/BUSINESS_PACKS.json` | `2d25c98a630ffa306f18340a143abe3ec871e978` | `7fe047d524f0431f111dbc4fed220d3215ba9030` | `SUPERSEDED_COMPATIBLE` |
| `ground/BUSINESS_PACKS.md` | `d139e1d1ac3f9ce34be36e03f01e7e8f76a9eacc` | `605bf46f727a5c5bcb54fd6848dbe7a79130a0bf` | `SUPERSEDED_COMPATIBLE` |
| `ground/BUSINESS_PACK_PAPERWORK.json` | `93305ff202526bb6b495efe43ed6297b0eaa2c34` | `c5b7a3166337cfecf9fd2a7213a18ca3d1da5740` | `SUPERSEDED_COMPATIBLE` |
| `ground/BUSINESS_PACK_PAPERWORK.md` | `105d8d28646da62a231c8fe6eae7a3930310cb64` | `26aad52d47772e876ac22a336624eb2ca9e3a9fb` | `SUPERSEDED_COMPATIBLE` |
| `host/business_pack_paperwork.py` | `2beb899e949f90dc162fe75c6494cb604af741a7` | `2beb899e949f90dc162fe75c6494cb604af741a7` | `PRESERVED` |
| `p/cursor-business-pack-paperwork-state-20260902-01.md` | `55aa15f1dbf3be9b34c4de2b9722b99227a5cd66` | `55aa15f1dbf3be9b34c4de2b9722b99227a5cd66` | `PRESERVED` |
| `packs/_template/paperwork.md` | `249b16c93ab1303703087fe1ba211661f472b0f4` | `dc3344b1d7ae131cb51e58f9895dc1ea666d5155` | `SUPERSEDED_COMPATIBLE` |
| `test_business_pack_paperwork.py` | `3a6727302bcdea5f478d783eae1a6384f5424bd0` | `3a6727302bcdea5f478d783eae1a6384f5424bd0` | `PRESERVED` |

`REAL_COLLISION = 0`.

## Contract reconciliation

The current original classifier remains byte-identical to the state-task land and still requires `state` alongside registration, EIN, sales tax, license, insurance, and contract. It remains non-gating and fail-closes invented checkout URLs, earnings copy, unsubstantiated “paperwork included” copy, filing-as-lawyer claims, legal/compliance door overclaims, and invented formation-partner links. An empty partner slot is allowed; an owner-pasted partner is allowed.

The current shared law/card/template and business-pack catalog/door still preserve the same state-specific/not-national contract, `OWNER_UNSET` / `HOLD_COUNSEL` boundaries, empty-until-owner-paste formation-partner slot, disclosure requirement, and the rule that checklists/links/templates are not tjlabs filing as the buyer's lawyer.

Later owners are compatible, not collisions:

- `cursor-business-pack-paperwork-included-20260902-01` is the separate factory-Do-X substantiation layer. Its helper explicitly says it does not write the state claim; its six homework sections measure the factory template, while the preserved original instance classifier/test still requires `state`.
- `cursor-business-pack-paperwork-slot-20260902-01` explicitly classifies paperwork as a shared factory slot, preserves `OWNER_UNSET` / `HOLD_COUNSEL`, excludes the LotRibbon plant instance, and marks the original paperwork helper/law/card/test/template/receipt as peer-owned paths it will not rewrite.

The ten commits from source snapshot `d56c11b0199d3fcf7820922023a3aa8d98370888` to fresh reviewed main `fb449442fe515b7912d81d886402e54a990b6d3c` touch no one of the nine reviewed paths, so the blob identities and semantic reconciliation above remain current at receipt publication.

## Independent VM execution

Direct shell network resolution to GitHub is unavailable in this VM, so connector reads—not shell cloning—were used to obtain current bytes. The current helper and current law were reconstructed locally and their Git blob identities were verified **before** execution:

- helper: `2beb899e949f90dc162fe75c6494cb604af741a7`
- law: `c5b7a3166337cfecf9fd2a7213a18ca3d1da5740`

Ten direct assertions then passed on those exact bytes:

1. fully populated state paperwork => `PAPERWORK_OK`
2. missing state => `PAPERWORK_INCOMPLETE`
3. “we set up your LLC” => `PAPERWORK_DOOR_OVERCLAIM`
4. unpasted partner URL => `PARTNER_LINK_INVENTED`
5. empty partner slot => allowed / `PAPERWORK_OK`
6. owner-pasted partner URL => allowed / `PAPERWORK_OK`
7. unfilled “paperwork included” => `PAPERWORK_CLAIM_UNSUBSTANTIATED`
8. filing-as-lawyer copy => `PAPERWORK_FILING_CLAIM`
9. earnings copy => `EARNINGS_IN_ADS`
10. invented Stripe checkout => `PAPERWORK_INVENTED_URL`

All assertions passed; both results remain `gate=false` / `commons_admission=false` where applicable.

## Hosted runner — intentionally nonterminal at publication

Disposable carrier branch: `sol-sol-vm/paperwork-state-current-tests-20260909-01`

- exact source parent: `d56c11b0199d3fcf7820922023a3aa8d98370888`
- carrier head: `6629af2db707de9ce914d5df569ae17bc5f43781`
- carrier diff: exactly one added file, `.github/workflows/sol-sol-vm-paperwork-state-current-tests-20260909-01.yml`
- GitHub Actions run: `34373889410`
- job: `102541671929`
- status at review publication: `queued`

The workflow is read-only (`contents: read`) and runs the original paperwork-state test, included-paperwork successor test, shared paperwork-slot successor test, shared unique-pack test, and focused `py_compile`. The carrier workflow is evidence-only and must **not** be merged.

A later reviewer/runner may convert the queue task to terminal `SHIPPED / REVIEWED` only after reading a terminal result for that run (or another exact-current equivalent), confirming the tested target bytes still match current main, and posting the durable terminal receipt. Do not spawn duplicate carriers while this run remains usable.

## Truth boundary

This review changes no product, test, template, catalog, checkout, provider, legal-service, customer, payment, marketing, advertising, or spend behavior. It performs no filing, partner enrollment, affiliate action, account mutation, outreach, or external transmission. It records source/history review plus exact-byte VM execution only; hosted success is explicitly not claimed while the Actions job is queued.
