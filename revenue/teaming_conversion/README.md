# Teaming Conversion Control

`revenue/teaming_conversion` is an offline control plane for the commercial handoff that begins **after a real buyer/prime/partner reply is retained** and before any owner-authorized follow-up is sent.

It exists to answer one narrow question: **given exact retained inbound evidence, current opportunity/source state, explicit asset-release policy, qualification gates, and owner-approved commercial facts, what is safe for an owner to review next?**

It does **not** infer customer acceptance from prose, contact anyone, send a reply, log into a portal, submit a bid, make a price/staffing/reference/certification/insurance commitment, sign anything, spend money, move funds, claim an award, or recognize revenue.

## Inputs and authority

The input packet (`teaming-conversion-input/v1`) binds:

- one opaque opportunity, counterparty and thread identity;
- retained inbound observations with exact message/content digests and an **owner-reviewed** interpretation enum (`POSITIVE_CONTINUE`, `REQUESTED_MORE_INFO`, `CONDITIONAL_INTEREST`, `DECLINED`, `AMBIGUOUS`);
- candidate follow-up assets, exact digests/versions, preparation state, and one of four release classes;
- independent owner release records for `OWNER_APPROVAL_REQUIRED` assets;
- qualification gates and optional commercial commitments.

The policy (`teaming-conversion-policy/v1`) owns reply/source freshness, future skew, required assets, and gates that must be exactly `CLEAR`.

The compiler never performs NLP or sentiment analysis. Caller text cannot mint a positive state; the retained observation must already contain the explicit owner-reviewed interpretation.

## Asset boundary

Release classes are:

- `PROSPECT_SAFE_SUMMARY`
- `PROSPECT_SAFE_PUBLIC_REFERENCE`
- `OWNER_APPROVAL_REQUIRED`
- `INTERNAL_ONLY`

`INTERNAL_ONLY` assets are never projected into the prospect-safe brief. `OWNER_APPROVAL_REQUIRED` assets are projected only when a retained release record exactly binds current asset ID, version and SHA-256. This prevents a prepared internal methodology, template, code artifact, or stale prior version from silently becoming customer-facing material.

## Dispositions

Exactly one disposition is emitted:

- `FOLLOWUP_READY` — owner review may proceed; **sending is still unauthorized**.
- `NEEDS_CLARIFICATION` — current retained reply is ambiguous or asks for factual clarification.
- `ASSET_PREP_REQUIRED` — continuation is supported but required prospect-safe material is absent, unready, internal-only, or unreleased.
- `QUALIFICATION_BLOCKED` — a mandatory qualification or required commercial fact is not clear/approved.
- `DECLINED` — current retained observation explicitly records a decline.
- `HOLD` — source/reply evidence is stale, future, conflicting, tampered, cross-thread, or otherwise unsafe.

A source/reply conflict takes precedence over all commercial dispositions. An explicit current decline precedes qualification/asset checks. Ambiguous/request-more-info observations precede readiness checks because there is no safe follow-up posture until the current ask is understood.

## Byte custody and verifier

`compile_bytes()` strict-parses the exact input and policy bytes, rejects duplicate JSON keys and non-finite numbers, and records SHA-256 for those exact byte streams (`custody_mode=exact_json_bytes`). The verifier recompiles from the same bytes at the receipt's exact trusted evaluation timestamp and requires byte-identical canonical receipt output.

The object API is explicit about weaker `canonical_objects` custody and has a separate verifier. This prevents a library caller from representing Python objects as exact consumed source bytes.

All durable identifiers are opaque refs. Bool/int aliases are rejected by exact built-in type checks. Timestamps use canonical whole-second UTC (`...Z`). Outputs are deterministic canonical JSON plus deterministic Markdown.

## CLI

Compile with host-owned current UTC:

```bash
python -m revenue.teaming_conversion.cli compile \
  --input packet.json \
  --policy policy.json \
  --json-output owner-review.json \
  --markdown-output owner-review.md
```

Verify exact source bytes later:

```bash
python -m revenue.teaming_conversion.cli verify \
  --input packet.json \
  --policy policy.json \
  --receipt owner-review.json
```

CLI inputs are opened as bounded regular files through one descriptor and read at most 1 MiB. Symlink/non-regular inputs fail closed where the platform supports `O_NOFOLLOW`. Outputs are create-exclusive ordinary files with no overwrite; if the second output fails, the first is removed so a compile does not leave a misleading partial pair.

## Authority ceiling

Every receipt embeds an all-false external authority matrix. Even `FOLLOWUP_READY` means **owner review only**. The module does not grant contact/send, portal, proposal/submission, commercial commitment, contract/signature, spend/payment, award/acceptance-claim, cash, or revenue authority.
