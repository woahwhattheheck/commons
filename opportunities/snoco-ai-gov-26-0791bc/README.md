# Snohomish County RFP-26-0791BC — bounded TJLabs evidence map

This package is a **pre-proposal truth boundary**, not a County response and not a representation that Token Junkie Labs is qualified to prime the solicitation. It answers one narrower question: *which public AI-governance scope signals can be mapped to landed, exact repository evidence today, and which claims must remain partner-owned, prohibited, or pending the full solicitation packet?*

## Public authority boundary

The published legal notice identifies **RFP-26-0791BC, AI Governance Solution** and a proposal deadline of **October 1, 2026 at 1:00 PM Pacific**, and points bidders to the Snohomish County ProcureWare portal for specifications. The full packet was **not retrieved by this workstream** because the portal requires an authenticated procurement workflow. Therefore this package does not invent scoring criteria, certifications, contract terms, mandatory integrations, legal interpretations, or submission requirements.

Current public sources used only as discovery/context:

- Published legal notice: https://sound.ipublishmarketplace.com/washington/advert/-general_18078
- County purchasing guidance (states the Purchasing Portal is the only official source for active solicitation documents): https://www.snohomishcountywa.gov/6004/Info-for-Suppliers
- County procurement portal: https://snoco.procureware.com/Bids
- Secondary scope listing: https://usesettle.com/rfp-hunter/ai-governance-solution-2337708
- Secondary timing/listing corroboration: https://www.cleat.ai/government/contracts/ai-governance-solution-f8s6

The secondary listing describes a broad AI-governance program including Shadow-AI discovery, policy-to-control enforcement, Microsoft 365 Government Community Cloud / Purview / Entra integrations, runtime drift and incident evidence, spend attribution, and training. Those details are encoded as **`secondary_scope_signal`**, never as County packet authority. Exact requirements stay `PACKET_REQUIRED` until an authorized operator retrieves the immutable packet/addenda.

## What the repository can substantiate now

Two landed Commons primitives support a bounded technical wedge:

1. `host/mcp_conformance.py` at Git blob `4db5e56f93fe609d0539ab270d088d5b1c23e6b0` records content hashes, bounded complete MCP discovery page ledgers, public-endpoint redaction, and optional named tool-call transport evidence.
2. `host/swarm_review.py` at Git blob `2f76e23572133de43bfae02a9c14c3c60f070a12` binds review decisions to exact source heads, content keys, work receipts, dependency read-sets, and current-main stability. Its own contract explicitly says model family is attested rather than authenticated.

That is enough to substantiate a **bounded evidence/receipt workstream**: content-addressed runtime/tool receipts, exact change-vs-approved-state evidence for software/configuration artifacts, and deterministic technical evidence packages useful during reconstruction. It is **not** enough to claim enterprise Shadow-AI discovery, Microsoft GCC administration, Purview DLP/eDiscovery, Entra identity controls, legal non-repudiation, Washington Public Records Act compliance, or prime-contractor status.

## Classification meanings

- `SUPPORTED_WEDGE` — exact landed repository evidence supports a narrow deliverable, with explicit limitations. Final fit still depends on the packet and prime architecture.
- `PARTNER_REQUIRED` — the public scope signal plausibly needs a product/integrator/discipline not evidenced by this repository.
- `CANNOT_CLAIM` — a status or capability must not be asserted for TJLabs from current evidence.
- `PACKET_REQUIRED` — the public material is insufficient to establish the solicitation requirement itself.

The current recommendation is deliberately **`TEAMING_WEDGE_ONLY_PENDING_PACKET`**. A credible prime or implementation partner would own Microsoft Government Cloud, Purview, Entra, County governance, public-records/legal controls, and production acceptance. TJLabs can offer the narrower deterministic runtime/change evidence layer if the packet and partner architecture actually call for it.

## Fail-closed validation

Run:

```bash
python3 opportunities/snoco-ai-gov-26-0791bc/validate_matrix.py \
  opportunities/snoco-ai-gov-26-0791bc/capability_matrix.json
```

The validator is offline and deterministic. It rejects, among other things:

- any boundary flag that upgrades TJLabs to prime, GCC/Purview/Entra implementer, PRA legal authority, or authorized submitter;
- a `SUPPORTED_WEDGE` with no exact pinned repository evidence, bounded deliverables, or non-claim limitations;
- an attempt to cite an unpinned path/blob as positive capability evidence;
- a packet-derived requirement while `county_packet_retrieved=false`;
- upgrades of protected rows such as M365 GCC/Purview, Entra, or PRA compliance;
- duplicate rows, unknown classifications, malformed source URLs, and incomplete authority records.

The emitted receipt contains raw and semantic SHA-256 digests plus classification counts. It does not contact the County, register for ProcureWare, send a clarification, set pricing, submit a proposal, read credentials, or authorize spend.
