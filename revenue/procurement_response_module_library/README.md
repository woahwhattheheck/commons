# Procurement Response Module Library

Deterministic, evidence-bound reuse for RFP/RFQ/procurement response material. The compiler prevents an old answer from becoming a current claim merely because it was copied into a new proposal.

The catalog carries 11 reusable response families: corporate capability, AI/data governance, cybersecurity, accessibility, implementation/delivery, SLA/support, staffing, references/past performance, pricing assumptions, subcontractor/partner matrix, and compliance crosswalk. Each module is versioned, owner-reviewed, time-bounded, tagged for applicability, and made only of claims with explicit evidence IDs. Evidence has a source reference, SHA-256, observation time, and state (`SUPPORTED`, `PARTIAL`, `MISSING`, or `NOT_APPLICABLE`).

A solicitation declares its required sections and tags. The compiler chooses the highest eligible module revision deterministically. Required sections fail closed to `HOLD` if no module matches, owner review is pending/denied, or any cited evidence is not supported. Optional sections may HOLD without blocking the whole packet.

`OWNER_REVIEW_READY` is **not** submission approval. Packet and receipt hard-code all of these as `false`: buyer contact, submission, signature, certification, price commitment, payment, and award/revenue recognition. External communication remains separately single-writer/Muse gated.

Strict input handling rejects duplicate JSON keys, floats/non-finite numbers, BOMs, invalid UTF-8, booleans in integer fields, duplicate module/evidence identities, future/stale evidence, unknown evidence references, and expired modules. Outputs are canonical JSON + Markdown + deterministic receipt. Verification recompiles from the exact input bytes and rejects any packet/Markdown/receipt tampering.

The included catalog/solicitation are **synthetic demo data only** and make no claim about TokenJunkieLabs, a buyer, references, certifications, acceptance, award, or revenue.

```bash
python -m revenue.procurement_response_module_library.engine compile \
  --library revenue/procurement_response_module_library/catalog.json \
  --solicitation revenue/procurement_response_module_library/solicitation.json \
  --out-dir /tmp/prm

python -m revenue.procurement_response_module_library.engine verify \
  --library revenue/procurement_response_module_library/catalog.json \
  --solicitation revenue/procurement_response_module_library/solicitation.json \
  --packet /tmp/prm/packet.json --markdown /tmp/prm/packet.md --receipt /tmp/prm/receipt.json
```
