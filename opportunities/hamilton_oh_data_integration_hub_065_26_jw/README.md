# Hamilton County, Ohio RFP 065-26/JW — Data Integration Hub

Recovered source-authority-bounded pursuit carrier for Commons issue #13928.

## Current disposition

`HOLD` — not a bid and not a no-bid. The public opportunity is visible, but the controlling Hamilton County solicitation packet/addenda have not been retained and source-admitted here. Public mirrors and caller-authored ledger rows may prioritize research; they cannot mint buyer requirements, qualification satisfaction, deadlines, teaming permission, or submission authority.

As checked on 2026-09-17, mirrors reported an October 14, 2026 response deadline and described a justice-data integration hub with API/event-driven integration, mapping/orchestration, validation, logging/monitoring, and NIEM/CJIS/FedRAMP-High themes. Those remain `DISCOVERY_ONLY` until recovered from controlling County material.

## Decision model

The compiler emits one of:

- `PRIME`: a source-owned retained controlling official packet is authenticated, official submission mechanics and a future official response deadline are bound, and every prime satisfaction gate has admissible retained evidence.
- `TEAMING`: the same retained official deadline is open, retained official material permits teaming, specialist delivery evidence is bound, and a real prime partner has source-owned due-diligence evidence.
- `HOLD`: authority, deadline, qualification, specialist, or partner gates remain incomplete.
- `NO_BID`: the source-owned retained official response deadline has passed.

### Requirement text is not qualification proof

`OFFICIAL_REQUIREMENT` can satisfy only the `submission_mechanics` gate. Eligibility, security/compliance, past performance, insurance/legal, and pricing require owner-specific satisfaction evidence (`OWNER_QUALIFICATION` or `OWNER_PRICING`). An RFP sentence describing a requirement cannot prove that the owner satisfies it.

### One source-owned trust root for official and internal evidence

Both buyer-control material and positive owner/partner evidence are closed-world. Runtime JSON may name only a JSON leaf directly under `retained_evidence/`, and that leaf is admissible only when `gate.py`'s `SOURCE_OWNED_RETAINED_EVIDENCE` mapping pins the exact leaf name to its exact SHA-256. The production map is intentionally empty in this carrier, so neither a controlling official packet nor positive owner/partner qualification is currently claimed.

For every admitted retained artifact the verifier requires source digest = locator digest = source-owned pinned digest; a one-link regular inode; no-follow directory-relative open; one unchanged file-descriptor generation; bounded UTF-8 strict JSON; and exact opportunity/source identity. Internal qualification artifacts additionally bind the exact requirement/evidence class plus typed non-empty facts/refs.

Official controlling packet/addendum artifacts use their own retained schema and bind exact source id, opportunity id, authority, URL, observed time, buyer-control claims, and controls. The runtime ledger's `OFFICIAL_CONTROLLING_PACKET` / `OFFICIAL_ADDENDUM` projection is compared as canonical exact-type JSON against that retained projection before it can set `official_packet`, deadlines, submission mechanics, teaming rules, or any other buyer-control field. Semantically equivalent timestamp spellings and Python equality aliases such as `true == 1` are not accepted as the same retained bytes. A fabricated ledger row with an arbitrary 64-hex digest therefore cannot mint `NO_BID`, `PRIME`, or `TEAMING`.

Raw JSON ingress is byte-bounded and fails closed on duplicate keys, floats/non-finite values, unsafe/oversized integer tokens, excessive nesting/parser recursion, invalid UTF-8 text, and other parser failures; CLI callers receive a deterministic gate error rather than an interpreter traceback.

The threat boundary is untrusted runtime JSON and retained-file substitution, not a malicious Python host. `SOURCE_OWNED_RETAINED_EVIDENCE` is reviewed program configuration. A trusted process owner that deliberately rebinds module globals, replaces functions, or mutates interpreter state is outside this contract; the gate does not claim hostile-process attestation.

`verify_receipt(...)` performs a semantic exact recompile against the source ledger, requirements, evidence manifest, source-owned retained bytes, and evaluation time. Rehashing a forged decision or authority bit does not verify.

## Immediate work order

1. Recover the exact official RFP and all current addenda from the County procurement portal. Retain exact bytes/digests, source-admit them, and identify the current generation.
2. Bind the official response/question deadlines, submission mechanics, teaming rules, evaluation criteria, security/compliance requirements, insurance, references, pricing forms, and addendum precedence from those retained bytes.
3. Add positive owner qualification only through reviewed source-owned retained artifacts; requirement text or runtime labels are not satisfaction evidence.
4. Re-evaluate prime economics without claiming justice-sector references, CJIS/FedRAMP authorization, insurance, certifications, pricing readiness, or capacity until source-owned evidence proves them.
5. If prime gates remain unproven and official rules allow subcontracting, identify a qualified prime and offer a paid specialist workshare. Any external contact must first win the fleet Muse single-writer collision gate.
6. Stop on an official deadline pass, official prohibition on teaming, or evidence that qualification/cost makes the pursuit uneconomic.

## Usage

```bash
python -m opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate \
  --ledger opportunities/hamilton_oh_data_integration_hub_065_26_jw/source_ledger.json \
  --requirements opportunities/hamilton_oh_data_integration_hub_065_26_jw/requirements.json \
  --evidence opportunities/hamilton_oh_data_integration_hub_065_26_jw/evidence_manifest.json \
  --now 2026-09-17T07:05:00Z
```

Output is canonical JSON with input digests and a semantic SHA-256 receipt. It grants no County contact, portal registration, question/proposal submission, signature, pricing commitment, partner representation, award, payment, receivable, or revenue authority.
