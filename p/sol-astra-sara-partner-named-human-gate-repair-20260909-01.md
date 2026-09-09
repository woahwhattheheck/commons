# SOL-ASTRA SARA named-human release-gate repair

Demand: `sara-partner-edna-accession-lims-01`
Date: 2026-09-09
Scope: bounded post-merge maintenance of the synthetic/read-only SARA partner accession shadow.

## Reproduced defect

Pinned landed source blob `13a36d09d9ca337b9bfb6e38b6a1cd65361ba09d` rejects exact reserved reviewer identities, but its `_named_human` tokenization only split underscores/hyphens. Reserved automation identities embedded as whitespace- or punctuation-separated tokens could therefore satisfy the two-token name check. Focused reproduction accepted examples including `System Reviewer`, `auto reviewer`, `AI Reviewer`, and `service account`.

## Repair

The reviewer-name gate now tokenizes on every non-alphanumeric separator, rejects any resulting token in the existing `RESERVED` set, and uses those same normalized tokens for the two-token human-name requirement. The reserved vocabulary itself is unchanged. No accession, classification, fixture, routing, qPCR, report, digest, replay, authoritative-state, or send semantics are changed.

Focused before/after gate checks cover eight reserved-token embeddings across whitespace, period, underscore, and hyphen separators; the repaired gate rejects all eight. Normal examples `Jordan Reviewer` and `Mary-Jane Reviewer` remain accepted. The original landed 10-test acceptance suite was inspected but is not re-counted here as a fresh execution receipt.

## Paths

- MODIFIED `revenue/production-lims/sara-partner-edna-accession/sara_partner_accession.py`
- NEW `revenue/production-lims/sara-partner-edna-accession/test_named_human_reserved_tokens.py`
- NEW this receipt

## Boundary

Synthetic/read-only repository maintenance only. No production/provider/customer/state write, biological interpretation, regulatory decision, external send, outreach, spend, owner-PC action, or force-push. Publication identifiers are carried by the authoritative GitHub/Slack integration receipt rather than recursively editing this file after merge.
