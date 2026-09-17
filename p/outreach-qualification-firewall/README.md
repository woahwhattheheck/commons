# Outreach Qualification Firewall v2

A deterministic, fail-closed pre-send gate for Token Junkie Labs revenue outreach. The package **never sends anything**.

## Authority model

`authorized_to_send` is deliberately impossible to mint from candidate JSON alone.

Current evaluation has three trust domains:

1. **Candidate packet** - opportunity/action facts and receipt *identifiers* only. It cannot carry a clock, owner approval object, Muse selection object, source path, or source digest.
2. **Repository-retained evidence** - the controlling source is selected only from `retained_sources/index.json`; owner and Muse receipts are selected only from `retained_authority/index.json`. Both indexes are raw-byte SHA-256 pinned in `firewall.py`. Files are opened beneath fixed package roots with no-follow, regular-file, single-hard-link, inode/generation checks.
3. **Process current time** - current send readiness calls the process clock internally. The CLI exposes no `--now`. An explicit `--historical-at` mode exists only for replay and is permanently non-authorizing, even when the packet references otherwise-valid owner/Muse receipts.

Adding or replacing a trusted source/authority receipt therefore requires changing repository-retained bytes **and** the pinned index digest under code review; changing a candidate packet is insufficient.

## Digest chain

The evaluator derives a stable `qualification_digest` over source identity + opportunity + route/registration + eligibility + economics + target/action + dedupe/prior-action facts. It then derives `action_digest` from the exact qualification digest, dedupe identity, and action.

An independently retained owner receipt must have:
- schema `tjlabs-owner-approval-receipt/v1`
- provider `TJLabsOwnerApproval`
- root `tjlabs-owner-root-v1`
- unique generation/source reference
- `APPROVED` status
- exact `qualification_digest`
- valid issued/expiry interval

An independently retained Muse receipt must have:
- schema `tjlabs-muse-writer-lease-receipt/v1`
- provider `SlackMuse`
- root `tjlabs-muse-root-v1`
- unique generation/source reference/key
- `SELECTED` status
- exact selected writer
- exact `action_digest`
- valid issued/expiry interval

Receipt byte SHA-256 values are themselves pinned in the retained authority index. Opportunity/action mutation therefore invalidates retained authority rather than silently inheriting it.

## Qualification gates

Current and historical evaluation both fail closed on:
- deadline/minimum runway;
- unproven response route or required registration;
- `UNKNOWN` / `FAILED` eligibility;
- non-positive/unbounded economics or unproven payment path;
- DNR/BOUNCE/BLOCKED/CLOSED relationship state;
- mismatched contact/transport;
- materially duplicate pending/sent/delivered/accepted/paid action.

`qualified_for_owner_review` is distinct from `authorized_to_send`. Owner/Muse authority cannot override qualification blockers.

## CLI

Current, process-time-owned evaluation:

```bash
python p/outreach-qualification-firewall/firewall.py packet.json --writer Z-Palisade-1445
```

Historical replay (always exit 2 / never authorizes):

```bash
python p/outreach-qualification-firewall/firewall.py packet.json \
  --writer Z-Palisade-1445 --historical-at 2026-09-17T19:00:00Z
```

There is intentionally no current-mode `--now` argument.

## Fixtures

- `qualified_owner_review.json` is complete enough for owner review but carries no authority receipt IDs.
- `authorized_example.json` references two independently retained **synthetic example-only** receipts bound to `Example Buyer` / `opps@example.com`. This proves the positive path without embedding any live lead or transport.
- `held_short_runway.json` is superficially attractive but fails historical minimum-runway evaluation.

The retained source and authority fixture roots are synthetic proof material only, not claims that any real buyer, owner, or Muse action occurred.

## Proof

```bash
python p/outreach-qualification-firewall/test_firewall.py
python -O p/outreach-qualification-firewall/test_firewall.py
```

The hostile suite kills the predecessor where candidate JSON self-authors `Bryce/APPROVED` and `SELECTED`; coordinated packet+explicit-clock rollback; historical replay with valid receipt IDs; owner/Muse transplant after action/opportunity mutation; foreign-writer reuse; unretained/pathlike receipt IDs; self-authored source path/digest; source-index resealing; hard-link and symlink aliases; deadline boundary/runway; unknown eligibility/payment; DNR dominance; bad economics; alias dedupe; and duplicate prior sends.

## Truth ceiling

This is pre-send decision support. It does not prove buyer/partner qualification beyond retained evidence, does not authenticate Slack/Gmail by itself, does not contact anyone, and does not establish submission, acceptance, award, payment, or revenue. The repository-retained authority store is an integration boundary: a trusted ingestion process must retain provider-origin receipts before current-mode authorization can become true for a real action.
