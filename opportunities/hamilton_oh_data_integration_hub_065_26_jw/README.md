# Hamilton County, Ohio RFP 065-26/JW — Data Integration Hub

Recovered source-authority-bounded pursuit carrier for Commons issue #13928.

## Current disposition

`HOLD` — not a bid and not a no-bid. The opportunity is publicly visible and appears open, but the controlling Hamilton County solicitation packet/addenda have not been retained in this carrier. Discovery mirrors are useful for prioritizing packet recovery and specialist/partner questions; they are never allowed to mint buyer requirements, qualification evidence, deadlines, or submission authority.

As checked on 2026-09-17, public mirrors report an October 14, 2026 response deadline and describe a justice-data integration hub with API/event-driven integration, mapping/orchestration, validation, logging/monitoring, and NIEM/CJIS/FedRAMP-High themes. Those claims remain `DISCOVERY_ONLY` until recovered from controlling County material.

## Decision model

The compiler emits exactly one of:

- `PRIME`: a controlling official packet is retained, official submission mechanics and a **future official response deadline** are bound, and every prime gate is backed by retained evidence whose class, source digest, requirement, and opportunity identity all match.
- `TEAMING`: the same future official deadline is bound, official material permits teaming/subcontracting, specialist delivery evidence is source/digest-bound, and a real prime partner is backed by retained due-diligence evidence.
- `HOLD`: potentially valuable, but authority, deadline, or qualification gates are incomplete.
- `NO_BID`: the retained official response deadline has passed.

Mirror sources (`MIRROR`) and the bare official portal entry (`OFFICIAL_PORTAL_ENTRY`) are structurally forbidden from controlling buyer fields such as deadlines, submission mechanics, teaming rules, evaluation criteria, or mandatory requirements.

Positive requirement state is closed-world. A `PROVEN` row must reference entries in `evidence_manifest.json`; each entry binds one requirement to this opportunity, an admissible evidence class, a retained source id, and the exact source SHA-256. Official requirement evidence must resolve to a retained `OFFICIAL_CONTROLLING_PACKET` or `OFFICIAL_ADDENDUM`.

Owner/partner evidence has a stronger source-tree trust boundary. An `INTERNAL_EVIDENCE` source cannot carry an inline semantic wrapper and hash it itself. Its `retained_artifact` locator must name one JSON file directly under this package's `retained_evidence/` directory and repeat the file SHA-256. The gate opens those exact repository-retained bytes itself, rejects traversal/symlinks/oversize/non-UTF-8/duplicate-key records, verifies the raw-byte digest, and then requires one exact record binding this opportunity, source id, requirement id, and admissible evidence class. The record must also contain the class-specific evidence kind plus non-empty substantive `facts` and `refs`.

That boundary deliberately moves positive owner/partner qualification out of caller packet authority and into source/code provenance. Writing or replacing retained-evidence files is a repository mutation and must be reviewed like source. The checked-in carrier currently retains **no positive owner/partner qualification record**; all real qualification rows remain `UNKNOWN`. Unit tests create temporary files inside `retained_evidence/` only to exercise the same production verifier contract, then remove them.

Unreferenced retained evidence and evidence left behind after a requirement falls out of `PROVEN` are rejected. Relabeling or transplanting a retained file cannot change its source-bound requirement/class. Byte drift invalidates the source digest.

`verify_receipt(...)` is a semantic verifier, not a rehash check. It exact-recompiles from the source ledger, requirements, evidence manifest, repository-retained evidence bytes, and evaluation time and compares the complete canonical packet. Rehashing a forged decision or authority bit therefore does not verify.

## Immediate work order

1. Recover the exact official RFP and all current addenda from the County procurement portal. Retain byte hashes and identify the current generation.
2. Bind official response/question deadlines, submission mechanics, teaming rules, evaluation criteria, security/compliance requirements, insurance, references, pricing forms, and addendum precedence.
3. Retain actual owner capability/qualification artifacts before marking any requirement `PROVEN`; runtime labels or self-authored inline wrappers are not evidence.
4. Re-evaluate prime economics. Do not claim TJLabs has justice-sector references, CJIS/FedRAMP authorization, insurance, or certifications unless retained owner/vendor evidence proves them.
5. If prime gates remain unproven and official rules permit subcontracting, identify a qualified prime and offer a paid specialist workshare around integration implementation, deterministic validation/evidence, cutover, observability, and test automation. External contact must use the fleet single-writer/Muse collision gate first.
6. Stop on an official deadline pass, official prohibition on teaming, or evidence that qualification/cost makes the pursuit uneconomic.

## Usage

```bash
python -m opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate \
  --ledger opportunities/hamilton_oh_data_integration_hub_065_26_jw/source_ledger.json \
  --requirements opportunities/hamilton_oh_data_integration_hub_065_26_jw/requirements.json \
  --evidence opportunities/hamilton_oh_data_integration_hub_065_26_jw/evidence_manifest.json \
  --now 2026-09-17T07:05:00Z
```

Output is canonical JSON with input digests and a SHA-256 receipt. Receipt authority is established only by semantic exact-recompile against those same retained inputs, retained source bytes, and evaluation time. The packet grants no County contact, portal registration, question/proposal submission, signature, pricing commitment, partner representation, award, payment, or revenue authority.
