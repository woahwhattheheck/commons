# Retain work when canonical document rows are malformed

## Existing consumer

`LiveCollectors._document` imports selected collections from an exact GitHub commit into the existing `WorkstreamStore`. A non-object or unkeyed row cannot establish a complete snapshot. The two formerly silent skips now raise the fixed `document_item_shape` source error; the existing collector error handling and SQLite ingestion retain the last good items and owner direction.

Valid empty collections still replace old contents. Existing `id`, `subject_id` and `record_id` mappings, multiple collection identities, pinned document URLs, normal updates and recovery remain unchanged. This extends PR10240's source-retention fixes to the existing document consumer; no store, schema, browser, provider, or import API is added or changed.

## Executed reproduction

Four fixture-provider/real-SQLite witnesses use null, unkeyed-object, string, and mixed valid/invalid rows. Each original-source result removes one saved work item while declaring complete coverage. Each corrected result reports `source_error`, removes zero, and retains the saved item and owner direction. These are constructed regressions, not assertions of live data loss or a production incident.

```sh
python -B -m unittest integrations.command_center.test_document_retention -v
```

Thirteen focused methods pass on the corrected source; exact pre-repair source fails eight with zero execution errors. Cases also exercise malformed later collections, existing missing/nonlist collection errors, valid empty clearing, normal recovery, both alternate ID fields and distinct collection IDs. Every provider fixture is read-only and verifies that the content request uses the resolved commit.

The combined Python command includes the five existing modules, PR10240's two modules, and this module:

```sh
python -B -m unittest \
  integrations.command_center.test_core \
  integrations.command_center.test_server \
  integrations.command_center.test_workstreams \
  integrations.command_center.test_collectors \
  integrations.command_center.test_work_integration \
  integrations.command_center.test_collector_response_shapes \
  integrations.command_center.test_collector_pagination_evidence \
  integrations.command_center.test_document_retention -v
```

Actual result: **121 methods, all passing**, 6.727 seconds on Python 3.13.5 in this cloud container. That consists of 66 original methods, 42 earlier response/pagination methods and 13 new document methods. The original and repaired outputs and full logs are retained. No live collection, provider mutation, external mail, game panel or deployment was executed.

## Source identity

| Input or output | Git blob |
| --- | --- |
| Collector before this change, containing PR10240 | ae30f9742afbd119c2bb721c6504394aee45bf21 |
| Collector after the two-line change | 6de1c521754a1f05cb9791239fc651782c7c99f4 |
| test_document_retention.py | 05775169c7c3fd9802a2386bf01576e3d9bebd12 |
| Existing core used by the tests | 77bf36d5480aa815ef835357e222576175aa5967 |
| Existing workstream store used by the tests | 7e3346b079bf6b1094b3e4ca0383c1657a2015c1 |
| Combined workflow with the new Python module | fa2fed6f346aa8236c2bc936c9518d663855ed54 |

Runtime SHA-256: `6b5ec56ee8e0a46c09920f748fe581ec064e8be2d9a577222d392b7799fecb84`. Test SHA-256: `d7be9224eed5e2d314026c1317da943ecccf094dde08a93f35a4bc6e7caab572`.

The existing command-center workflow adds this one Python module and retains COORD's `test_web.cjs` plus `test_work_detail.cjs` Node command. The local Python result does not claim execution of the newly composed Fleet UI; hosted workflow results are recorded separately on the PR.

Ownership and exact reproduction handoff: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788844998314339?thread_ts=1788754579.213779&cid=C0BRGMDQB6G

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../titanmcp.html). Cite Latch Pad KEEP.
