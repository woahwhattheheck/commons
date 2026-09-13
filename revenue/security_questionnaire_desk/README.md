# Security Questionnaire Desk

`Security Questionnaire Desk` is an **offline fulfillment compiler** for the existing Commons human-outcomes candidate `ho-security-questionnaire` ($3,000 / 10 calendar days in the current catalog). It does not promote that candidate, publish a checkout, contact a buyer, or claim demand. It makes the fulfillment promise mechanically safer: every required questionnaire row is represented as an evidence-backed proposed answer, `UNMEASURED`, `OWNER_INPUT_REQUIRED`, or `HOLD`, with exact question/evidence lineage and a separate owner-review generation.

The strongest product output is an owner-approved return set. That means only that the supplied, PII-minimized questionnaire and evidence were compiled under these rules and the owner disposition still matches the exact answer generation. It is **not** a certification, compliance determination, security audit, legal conclusion, buyer acceptance, provider state, payment, or recognized revenue.

## Contract

The compiler accepts one strict JSON object containing:

- one opaque questionnaire identity, source ref, and SHA-256;
- exact question rows (`BOOLEAN`, `TEXT`, `ENUM`, or `MULTI`) with immutable source refs/digests and an explicit `GENERAL` or `CERTIFICATION` assurance kind;
- an evidence library with immutable evidence IDs, an explicit supported question ID plus exact question source-row SHA-256, claim key/value, statement, evidence kind, `PUBLIC` / `NON_PUBLIC` disclosure, source ref/digest, capture time, and freshness window;
- exactly one proposed answer per question; and
- optional owner dispositions bound to the exact compiled `answer_generation_sha256`.

A `SUPPORTED_PROPOSED_ANSWER` requires current cited evidence scoped to that exact question ID and question source-row SHA-256; unrelated evidence forces `HOLD` with `EVIDENCE_SCOPE_MISMATCH`. Evidence with the same claim key but conflicting claim values makes the answer `HOLD`. A `CERTIFICATION` question cannot be supported unless at least one current cited row is explicitly `CERTIFICATION_REFERENCE`; otherwise it `HOLD`s instead of minting a certification from generic documents or owner prose. Future/stale evidence cannot support a measured answer.

`NON_PUBLIC` evidence may appear in the internal owner-review packet. The generated `public-safe.json` strips all non-public statements/source refs and degrades a supported answer that depends on private evidence to `UNMEASURED`. The public-safe artifact is not a buyer-send action; it is only a leak-resistant projection.

## Production commands

```bash
python revenue/security_questionnaire_desk/security_questionnaire_desk.py compile \
  revenue/security_questionnaire_desk/example_input.json \
  /tmp/security-questionnaire-output
```

Production compile takes **current process UTC itself**. There is deliberately no `--as-of` argument that can backdate stale evidence. Compilation publishes five create-exclusive files into a new or empty ordinary directory:

- `packet.json` — canonical internal review packet;
- `review.md` — human-readable owner review;
- `answers.csv` — deterministic answer matrix;
- `public-safe.json` — non-public evidence stripped;
- `receipt.sha256` — packet receipt.

Verification replays the packet at its bound compile time, then uses **fresh current process UTC** to ensure evidence supporting measured answers has not expired:

```bash
python revenue/security_questionnaire_desk/security_questionnaire_desk.py verify \
  revenue/security_questionnaire_desk/example_input.json \
  /tmp/security-questionnaire-output/packet.json
```

A packet therefore remains verifiable while its exact supporting evidence is current and fails closed after support expiry or any source/question/answer/disposition/receipt drift.

## Input safety

Input is strict UTF-8 JSON with duplicate-key rejection, no floats/non-finite values, bounded integers/arrays/text, exact-key schemas, canonical whole-second UTC, lowercase SHA-256, and obvious direct-contact PII / secret-shaped durable material rejection. Files are read through one bounded regular-file descriptor generation with symlink and pathname-replacement fences.

Outputs are create-exclusive. Existing files and final symlinks are refused. If a later multi-file publication step fails, the compiler **does not delete already visible output paths by pathname**, because a concurrent actor could have replaced them; partial publication is safer than deleting a foreign replacement.

## Owner review lineage

An owner disposition is one of:

- `APPROVED_FOR_RETURN`
- `REVISE`
- `REJECT`

It binds the exact `answer_generation_sha256`, which commits the question digest, proposed answer/state, effective state, and sorted cited evidence IDs/digests. Changing a question, answer, evidence bytes, or effective state makes the older disposition `STALE_GENERATION`. `APPROVED_FOR_RETURN` on a `HOLD` or unresolved `OWNER_INPUT_REQUIRED` row is invalid; owner input must be resolved into a returnable answer generation first.

## Validation

Run the focused hostile suite in both ordinary and optimized Python:

```bash
python -m unittest -v revenue/security_questionnaire_desk/test_security_questionnaire_desk.py
python -O -m unittest -v revenue/security_questionnaire_desk/test_security_questionnaire_desk.py
python -m py_compile \
  revenue/security_questionnaire_desk/security_questionnaire_desk.py \
  revenue/security_questionnaire_desk/test_security_questionnaire_desk.py
```

Coverage includes deterministic replay/order invariance, cross-question evidence rejection, unsupported certification, stale/future/conflicting evidence, exact owner-generation binding, changed evidence/question input, packet receipt tamper, evidence expiry at verify time, duplicate JSON keys, bool/int and float traps, secret/PII-shaped material, private-evidence public-export stripping, create-exclusive publication, final symlink refusal, descriptor-bound input, and absence of a caller-controlled production clock.

## Authority ceiling

This product has **no authority** to contact a buyer/customer, send a questionnaire, access a CRM/provider/account, run a security scanner, create a certification/compliance claim, sign a contract, publish/promote the catalog candidate, create checkout, charge/refund/move money, or recognize revenue. The existing candidate price/status are read-only catalog facts.
