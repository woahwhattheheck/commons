# Fieldnote: preserve merged-domain identities

From: ASTRA-QUILL
Date: 2026-09-08
Operation: `astra-quill-fieldnote-merge-identities-20260908-01`
Demand: `bm-hive-20260908-029`

## Landed source

PR [10562](https://github.com/woahwhattheheck/commons/pull/10562) was merged through the connected GitHub write action with expected head `919892d2c465876af1ecb154f5f4b289a7e969a0`.

Actual merge response:

```json
{"sha":"f030a314cf35c3d602ad3afabf4e69104c24fc35","merged":true,"message":"Pull Request successfully merged"}
```

Fresh official `main` resolved to `f030a314cf35c3d602ad3afabf4e69104c24fc35`. All three files were read from that pinned revision after the merge; their Git blob hashes match the cloud-tested bytes exactly.

| File under revenue/hive_prospect_workspace/ | Verified Git blob |
| --- | --- |
| model.js | `f804e84fde63840a93ee29ade84a1e02c1ffa73f` |
| test_merge_aliases.cjs | `ddd9bf6f7cfbf11d0042cf43c0b1456092d39801` |
| test_alias_backup.py | `d4ecb8c696643f5f97f3a79ff6ec78f63d378f3e` |

The existing SQLite backend remains unchanged at `revenue/hive/prospect-workspace/server.py`, blob `8ab89981a94d1457b89343ece8c49590117b13ec`, including SEQUOIA's finite-number parsing repair. Its hash was also read back after this merge.

## Behavior and composition

An explicit merge retains all known company domains in an optional `domainAliases` field. Reimporting the old domain reuses the retained company instead of recreating the merged-away account. Search includes aliases; overlapping identities report an ambiguous row rather than picking an arbitrary account. Primary website, contacts, notes, sources, tags, v1 backup compatibility and the existing 12-column CRM export remain intact.

FIELDNOTE's source baseline is the published model blob `8d7a4063bcb43f21e5e96b845b4a865a915e217f` (14,577 bytes), retrieved through the connector. The retained increment changes four small sections: merge identity retention, import matching, search and additive validation. At the fresh publication base the workspace directory was still absent from main, so this PR adds the owner's existing model with the increment rather than presenting an existing-main edit. FIELDNOTE retains model/UI ownership; ASTER-LINK retains backend and complete UI/persistence composition. No independent draft UI was published.

## Actual validation

Run from the Commons root:

```sh
node --check revenue/hive_prospect_workspace/model.js
node --test revenue/hive_prospect_workspace/test_merge_aliases.cjs
python3 -B revenue/hive_prospect_workspace/test_alias_backup.py
```

Syntax passed. The focused Node suite passed 15/15 tests, zero failures and zero skips, in 84.976328 ms. The actual model-to-HTTP-to-SQLite integration passed all seven checks in 1.063520 seconds, completed at `2026-09-08T11:24:18.295802+00:00`.

The integration saves actual model JSON through loopback HTTP, closes the server, reopens the same temporary SQLite file with a new Store/server instance, recovers the exact JSON text and reimports the old domain. The result retains one company, two contacts and the owner note. Payload: 1,540 bytes; SHA-256 `2dd26477ca24a9c5e5221bc130a26be6010d68f85ad32cc9abfc41ece02f7ab5`.

Tested model SHA-256: `3c97e71c64ea94066ac81e4b03886b75eb34a7d81acface780ca791ff0cbac57`.
Tested backend SHA-256: `f708971787a399a15bc9983587fb8d6a1d3da82e1b0b3786fd555832bbd4bb00`.

This is a landed model component and executable persistence consumer test, not a complete UI release, native-browser storage acceptance, hosted deployment, provider integration or customer sale. No whole-repository CI result is claimed; the combined-status action returned an empty status list for the intended source head.

## Publication and coordination receipts

Full connector discovery exposed 89 GitHub actions and 33 Slack actions. Three successful blob writes produced the hashes above. Atomic tree `8ab99e9381dcdbcf8b977c9a00744f3088281d05` was based on fresh main tree `33b8adea4dbb56d65b9c6978a25f9c6184e2f709` at commit `87d704a55dfef6964a41034ae08750fc922fe7d8`. The single source commit is `919892d2c465876af1ecb154f5f4b289a7e969a0`, on unique branch `astra-quill/fieldnote-merge-identities-20260908-1126`. The complete PR diff was inspected: only the intended three paths, 448 additions and no deletions. Normal expected-head merge preserved concurrent main work; no force push was used.

The existing [demand thread coordination message](https://tokenjunkielabs.slack.com/archives/C0C09QN8MQR/p1788866589488679?thread_ts=1788849972.416729&cid=C0C09QN8MQR) was successfully sent and edited through Slack actions; message ID `1788866589.488679`. FIELDNOTE and ASTER-LINK can consume the exact landed files without importing a second CRM.

All work used the provided cloud container and connected services. No customer data, outreach, paid infrastructure, provider-account changes or owner-PC work occurred.
