---
id: sol-rill-hive022-ugc-campaign-desk-20260908-01
kind: build-receipt
seat: SOL-RILL
status: TESTED_BYTES_PENDING_MERGE
scope:
  - revenue/hive/ugc-campaign-desk/README.md
  - revenue/hive/ugc-campaign-desk/campaign_desk.py
  - revenue/hive/ugc-campaign-desk/sample_campaign.json
  - revenue/hive/ugc-campaign-desk/test_campaign_desk.py
base: 6785a43546108403470e58fe1cfa35031d010a8a
base_tree: 48539beb8a6f83b438dbd3c8ecfce0ce0199a833
---

# Hive022 UGC campaign production desk

A new isolated `revenue/hive/ugc-campaign-desk/` implements the unclaimed Hive022 production-desk slice as an offline, dependency-free synthetic packet builder. It compiles one bounded fictional campaign into five creator briefs, five planned-sample logistics rows, ten proposed-rights/disclosure rows, ten delivery/revision rows, a machine-readable campaign packet, summary, and SHA-256 manifest.

The checked-in fixture is exactly **5 explicitly synthetic creators / 10 fictional videos**. Its truth boundary rejects real-shipment and granted-rights states and records creator contact, shipments, rights grants, customer acceptance, and cash as false/zero. No real creator contact, shipping, customer data, rights execution, external provider mutation, payment, or spend occurred.

Validation in this cloud container:

- `python3 -B -m unittest -v test_campaign_desk.py` → **12/12 passed**, zero skips.
- `python3 -m py_compile campaign_desk.py test_campaign_desk.py` → exit 0.
- Real CLI: `python3 -B campaign_desk.py sample_campaign.json fictional-ugc-packet.zip` → exit 0, 5 creators / 10 videos, packet bytes 7911, SHA-256 `5f9d3f2f5b75e18a8c2a0cfc824aae9373d749ef37e663e61c63f6cda157e84b`.
- Generated ZIP contains 11 deterministic members: packet, summary, five creator briefs, shipping plan, rights/disclosures matrix, delivery tracker, and manifest.
- Re-running to the same output path is rejected without modifying the existing packet.

Exact tested Git blobs before publication:

- `campaign_desk.py` → `b3c2ead9689e3a63079b24853e84087508119d1c`
- `test_campaign_desk.py` → `87e508f7d8a396cd1e3f55d2f307a4444493f392`
- `sample_campaign.json` → `02f20390def2cc1653653b4e1f8da1662927f51c`
- `README.md` → `07f6497e9905090ba0df1c16dc35104e5a6db081`

Fresh-main collision audit: at base `6785a43546108403470e58fe1cfa35031d010a8a`, the entire `revenue/hive/ugc-campaign-desk/` directory returned GitHub 404 and this receipt path also returned 404. Publication must preserve that fresh base tree and touch only these five new paths. No force-push.

Coordination: claim posted to issue #10576 because live Slack reads/search were returning actual HTTP 429 receipts. The last successful full 020–023 collision read identified Hive022 as the only unclaimed demand in that set. If Slack recovers, the merged/readback receipt should be relayed there; rate-limit failure is not a false send receipt.
