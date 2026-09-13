# Official-packet recovery and source-binding runbook

The current seat did **not** acquire the controlling Oklahoma packet. This runbook makes that gap explicit and recoverable without inventing evidence.

## 1. Start from the official NASPO route

Use NASPO ValuePoint's SW1045 solicitation page and its `View RFP` link. Do not substitute a mirror download for the controlling source.

If the Oklahoma portal requires an authenticated supplier session, acquisition must be performed only by an owner-authorized person/session. This package does not register, log in, accept portal terms, or submit anything.

## 2. Capture the full inventory before qualification

Acquire, at minimum, the complete RFP overview/instructions plus **every** attachment, form, workbook, sample agreement and addendum visible for the current event/version. The five filenames in `attachment_manifest.json` are mirror-discovered names, **not** a declaration of completeness.

Record for each file:

- exact official filename;
- official event/version;
- official URL or portal document identity;
- byte length;
- SHA-256 of the exact downloaded bytes;
- capture time;
- whether it is current/superseded;
- addendum relationship.

## 3. Confirm addenda state independently

Prime readiness requires `official_addenda_inventory_confirmed=true` in both source and attachment manifests. Do not infer “no addenda” because none are mentioned by a mirror.

Before final proposal authorization, repeat the official inventory and compare document IDs/digests.

## 4. Promote sources deliberately

Only after exact official bytes exist:

- set document `discovery_authority=OFFICIAL_PACKET`;
- set `status=OFFICIAL_EXACT`;
- bind `official_url` / portal identity and SHA-256;
- set complete inventory/addenda flags only when actually verified;
- bind the aggregate packet digest and attachment count;
- extract category requirements to `requirements.json` with source-document hashes;
- capture the exact evaluation model from the controlling document.

Mirror observations remain labeled mirror observations; they are not silently promoted.

## 5. Re-run hostile validation

Run normal and optimized suites, compile a fresh receipt using an out-of-band trusted current time, and verify the receipt. Then inspect:

- both prime categories independently;
- every unmapped / non-PROVEN mandatory requirement;
- reference and personnel evidence;
- partner commitment evidence;
- pricing units;
- source freshness and deadline.

## 6. Final pre-submission fence

A `PRIME_READY_FOR_OWNER_REVIEW` state is not submission authority. A human still must separately authorize representations, names, prices, certifications/signatures and portal submission against the then-current official packet.
