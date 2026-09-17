# Procurement award source adapters

Operation: `PROCUREMENT-AWARD-SOURCE-INGEST-ADAPTERS-20260916-ZSOL`  
Issue: `#15128`

This layer turns retained, explicitly structured public-procurement source payloads into the exact input consumed by `engine.py`. It exists so award, bid-tabulation, executed-contract, and amendment/option evidence can be ingested reproducibly instead of hand-normalized before each price review.

## Truth boundary

`source_adapters.py` is a **parser and evidence-preservation layer, not a provider authenticator**.

The request carries retained source metadata: URI, raw-source SHA-256, observed time, authority classification, source class, and title. The adapter:

- preserves retained metadata exactly after validation;
- accepts only credential-free HTTPS source locators with no query, fragment, or userinfo component;
- recursively percent-decodes a locator for admission checks, so encoded or multiply encoded query/fragment/userinfo forms cannot be retained, while ordinary encoded path octets such as `%20` or `%2F` remain allowed and are preserved byte-for-byte in the retained URI;
- verifies that `payload_sha256` matches the canonical structured payload it actually parsed;
- treats the retained raw-source SHA-256 as one generation identity inside a compile: the same claimed raw source cannot be reminted under a fresh `source_id`, URI, adapter, or payload and counted again;
- independently treats the verified canonical structured-payload SHA-256 as a second generation identity, so identical structured evidence cannot be cloned merely by changing caller-controlled metadata;
- requires legitimate multiple rows from one retained raw source to live inside that source's single structured payload;
- never upgrades `SECONDARY_INDEX`, `SELF_AUTHORED`, or `SYNTHETIC_FIXTURE` to `BUYER_OFFICIAL`;
- records provider/buyer authentication and every commercial authority as false;
- feeds normalized bytes into the price-intelligence compiler, which applies stale/conflict/comparability rules at **economic-claim** granularity.

A caller can lie about a URI, raw-source digest, or authority label. This module does not make those labels cryptographically or provider-authenticated. Production use therefore still requires upstream retention/review of the actual buyer source. The adapter receipt proves deterministic transformation of supplied evidence; it does not prove that a buyer published it.

## Claim-level weighting

Literal source/payload dedupe is not the statistical authority boundary. Two genuinely different buyer documents can corroborate the same economic claim.

The downstream engine groups fresh buyer-official observations by `claim_key` before computing comparable statistics:

- identical economic signatures under one claim (`opportunity_id`, vendor, amount, currency, basis, unit, term, price kind) contribute **one** comparable statistical row;
- corroborating `source_ids` are unioned onto that representative row so evidence provenance is retained;
- different signatures under one claim are **not** collapsed and continue to produce `HOLD_SOURCE_CONFLICT`;
- distinct claims with the same price still count independently.

This prevents an award notice plus executed contract—or the same logical award reminted under a changed document identifier—from inflating count/range/median weight while retaining legitimate corroboration.

## Supported shapes

### `AWARD_NOTICE_JSON_V1`
Compatible source classes: `AWARD_NOTICE`, `BOARD_AWARD`. Explicit opportunity, award ID, vendor, amount, currency, basis, unit, term, and date become `AWARD`; ambiguous/incomplete fields HOLD instead of being guessed.

### `BID_TABULATION_JSON_V1`
Compatible source class: `BID_TABULATION`. Only responsive rows with explicit amounts and complete basis/unit/term semantics become `BID`. Multiple legitimate vendor rows belong in the one retained tabulation payload.

### `EXECUTED_CONTRACT_JSON_V1`
Compatible source class: `EXECUTED_CONTRACT`. Explicit base value becomes `AWARD`; separately explicit option value remains `OPTION` and is never folded into the base.

### `AMENDMENT_OPTION_JSON_V1`
Compatible source class: `AMENDMENT`. Explicit amendment/option values remain `OPTION`; they are never promoted to `AWARD`.

## Hold-not-guess rules

The adapter does not infer amount from prose, unit from a rate, term from dates, base by subtracting options, total by adding options, responsiveness from rank, award status from bid position, currency conversion, or buyer-officialness from a hostname.

Representative HOLD codes include `AMBIGUOUS_AMOUNT`, `MISSING_TERM`, `MISSING_RATE_UNIT`, `UNEXPECTED_LUMP_UNIT`, `NONRESPONSIVE_BID_EXCLUDED`, `OPTION_TERM_MISSING`, `OPTION_NON_ANCHOR`, `CHANGE_RECORD_NON_ANCHOR`, and `SOURCE_NOT_BUYER_OFFICIAL`.

Malformed structure, duplicate JSON keys, non-integer JSON numbers, bool-as-money, duplicate source IDs, duplicate retained raw-source generations, duplicate structured payload generations, duplicate row IDs, bad hashes, HTTP/credentialed/query-bearing/fragment-bearing locators (including recursively encoded forms), incompatible source classes, and payload-hash mismatches fail closed.

## Artifacts

Compile:

```bash
python -m revenue.procurement_award_price_intelligence.source_adapters \
  compile \
  --input revenue/procurement_award_price_intelligence/source_adapters_example.json \
  --out-dir /tmp/procurement-adapter-generation
```

Compile creates one previously nonexistent generation directory containing `price_input.json`, `adapter_packet.json`, and `adapter_receipt.json`. The directory is create-only; a second compile to the same path fails instead of overwriting the first generation.

Verify:

```bash
python -m revenue.procurement_award_price_intelligence.source_adapters \
  verify \
  --input revenue/procurement_award_price_intelligence/source_adapters_example.json \
  --price-input /tmp/procurement-adapter-generation/price_input.json \
  --packet /tmp/procurement-adapter-generation/adapter_packet.json \
  --receipt /tmp/procurement-adapter-generation/adapter_receipt.json
```

`verify` recompiles the complete generation and requires byte-identical normalized input, packet, and receipt.

## Authority ceiling

No buyer/prime contact, portal/account mutation, quote, bid, submission, signature, price commitment, award recognition, invoice, payment, or revenue recognition is authorized. The strongest result remains internal price research from retained source evidence.

## Verification

`test_source_adapters.py` covers all four source shapes, source-class fencing, secondary-source non-promotion, payload/source digests, ambiguous/nonresponsive rows, option separation, malformed money/JSON, URI constraints, duplicate identities, deterministic receipts, output tamper, create-only CLI publication, and direct consumption by the price engine.

`test_source_adapters_redclosure.py` pins the STOP-MERGE predecessors and their positives: literal/encoded/double-encoded query/fragment and encoded-userinfo locators fail closed; ordinary encoded paths remain exact; raw-source and canonical-payload remints are fenced; changed document identity cannot add statistical weight; independent award-notice + executed-contract corroboration contributes one claim while preserving both sources; differing same-claim signatures still HOLD conflict; distinct claims still count separately; legitimate multi-row bid tabulations remain supported.

`test_engine.py` independently pins claim-level collapse/provenance preservation and the distinct-claim positive. The retained procurement recipe runs engine, current-main adapter, source-adapter, and red-closure suites under normal and optimized Python.

Current main retains `procurement-award-price-intelligence.yml` under `ci/workflow-recipes/` rather than the active `.github/workflows/` surface. That recipe is the functional-test specification; repository `source-parses` separately provides hosted Python syntax parsing when Python paths change. No extra runner matrix or active workflow surface is added.