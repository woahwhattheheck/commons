# Procurement award source adapters

Operation: `PROCUREMENT-AWARD-SOURCE-INGEST-ADAPTERS-20260916-ZSOL`  
Issue: `#15128`

This layer turns retained, explicitly structured public-procurement source payloads into the exact input consumed by `engine.py`. It exists so award, bid-tabulation, executed-contract, and amendment/option evidence can be ingested reproducibly instead of hand-normalized before each price review.

## Truth boundary

`source_adapters.py` is a **parser and evidence-preservation layer, not a provider authenticator**.

The request carries retained source metadata: URI, raw-source SHA-256, observed time, authority classification, source class, and title. The adapter:

- preserves that metadata exactly;
- accepts only credential-free HTTPS source locators with no query or fragment component, so signed/token-bearing locator material cannot be retained or exported;
- verifies that `payload_sha256` matches the canonical structured payload it actually parsed;
- treats the retained raw-source SHA-256 as one generation identity inside a compile: the same claimed raw source cannot be reminted under a fresh `source_id`, URI, adapter, or payload and counted again;
- independently treats the verified canonical structured-payload SHA-256 as a second generation identity, so identical structured evidence cannot be cloned into statistics merely by changing caller-controlled source ID, URI, or claimed raw-source SHA metadata;
- requires all legitimate rows extracted from one retained raw source to live inside that source's single structured payload (for example, all bid-tabulation rows live under one `BID_TABULATION_JSON_V1` document);
- never upgrades `SECONDARY_INDEX`, `SELF_AUTHORED`, or `SYNTHETIC_FIXTURE` to `BUYER_OFFICIAL`;
- records `source_provider_authenticated=false` and `buyer_officialness_authenticated=false`;
- feeds normalized bytes into the landed price-intelligence compiler, which still applies stale/conflict/comparability rules.

A caller can lie about a URI, raw-source digest, or authority label. This module does not make those labels cryptographically or provider-authenticated. Production use therefore requires the upstream source-capture process to retain and review the actual public buyer source. The adapter receipt proves deterministic transformation of the supplied generation; it does not prove that a buyer published it. The structured-payload duplicate fence is deliberately independent of caller raw-source metadata so an identical parsed evidence object cannot gain extra weight just because that metadata is reminted.

The one-generation rule is deliberately conservative. If a buyer document contains multiple legitimate bid or tabulation rows, retain that source once and place all rows inside its one structured payload. Do not split or reslice the same retained bytes, or clone an identical structured payload under fresh metadata, into multiple top-level documents merely to create additional observations.

## Supported shapes

### `AWARD_NOTICE_JSON_V1`

Compatible source classes: `AWARD_NOTICE`, `BOARD_AWARD`.

Required explicit fields: opportunity ID, award ID, vendor, amount in minor units, currency, basis, unit, term months, award date. The observation is `AWARD`. Missing amount, missing term, or contradictory basis/unit semantics produce HOLD records and no price observation.

### `BID_TABULATION_JSON_V1`

Compatible source class: `BID_TABULATION`.

The document fixes opportunity/tabulation identity, currency, basis, unit, term, and bid date. Each row must have a row ID, vendor, bid amount in minor units (or `null` when not explicit), and a real JSON boolean `responsive`. Only responsive rows with explicit amounts and complete basis/unit/term semantics become `BID` observations. Nonresponsive or ambiguous rows remain auditable HOLDs. Multiple legitimate bid rows belong inside this one retained source payload and do not require multiple source identities.

### `EXECUTED_CONTRACT_JSON_V1`

Compatible source class: `EXECUTED_CONTRACT`.

An explicit base contract amount becomes an `AWARD` observation. A separately explicit option amount is **never added to the base**: it is retained as an `OPTION` observation and marked `OPTION_NON_ANCHOR`, so the price engine cannot silently treat potential option value as current award price.

### `AMENDMENT_OPTION_JSON_V1`

Compatible source class: `AMENDMENT`.

Explicit amendment or option values are retained as `OPTION` observations only. They are never promoted to `AWARD`, even when buyer-official. This prevents a change order, exercise, or amendment delta from being treated as the original comparable award.

## Hold-not-guess rules

The adapter does not infer a money value from text, a unit from a rate, a term from dates, base value by subtracting options, total value by adding base and options, responsiveness from rank, award status from bid position, currency conversion, or buyer-officialness from an HTTPS hostname.

Representative HOLD codes are `AMBIGUOUS_AMOUNT`, `MISSING_TERM`, `MISSING_RATE_UNIT`, `UNEXPECTED_LUMP_UNIT`, `NONRESPONSIVE_BID_EXCLUDED`, `OPTION_TERM_MISSING`, `OPTION_NON_ANCHOR`, `CHANGE_RECORD_NON_ANCHOR`, and `SOURCE_NOT_BUYER_OFFICIAL`.

Malformed structure, duplicate JSON keys, non-integer JSON numbers, bool-as-money, duplicate source IDs, duplicate retained raw-source generations, duplicate structured payload generations, duplicate row IDs, bad hashes, HTTP/credentialed/query-bearing/fragment-bearing URIs, incompatible source classes, and payload-hash mismatches fail closed.

## Artifacts

Compile:

```bash
python -m revenue.procurement_award_price_intelligence.source_adapters \
  compile \
  --input revenue/procurement_award_price_intelligence/source_adapters_example.json \
  --out-dir /tmp/procurement-adapter-generation
```

Compile creates one previously nonexistent generation directory containing:

- `price_input.json` — exact downstream `engine.py` input;
- `adapter_packet.json` — source audit, HOLDs, downstream status, and authority ceiling;
- `adapter_receipt.json` — request/output hashes and authority ceiling.

The directory is create-only. A second compile to the same path fails instead of overwriting the first generation.

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

No buyer or prime contact, portal/account mutation, quote, bid, submission, signature, price commitment, award recognition, invoice, payment, or revenue recognition is authorized by this layer. The strongest result remains internal price research from retained source evidence.

## Verification

`test_source_adapters.py` covers all four source shapes, source-class fencing, secondary-source non-promotion, payload/source digests, ambiguous/nonresponsive rows, option separation, malformed money/JSON, URI constraints, duplicate identities, deterministic receipts, output tamper, create-only CLI publication, and direct consumption by the landed price-intelligence engine.

`test_source_adapters_redclosure.py` pins the STOP-MERGE predecessors: query/fragment-bearing source locators fail closed; one claimed raw source cannot be reminted or resliced into another top-level document; an identical canonical structured payload still cannot be reminted when caller-controlled raw-source metadata is changed; and multiple legitimate rows remain supported inside one retained source payload. The retained procurement recipe runs the engine suite, current-main adapter suite, source-adapter suite, and red-closure suite in both normal and optimized Python.

Current main retains `procurement-award-price-intelligence.yml` under `ci/workflow-recipes/` rather than the active `.github/workflows/` surface. The recipe remains the functional-test specification under Python 3.13; repository-level `source-parses` separately provides hosted syntax parsing when Python paths change. No extra runner matrix or active workflow surface is added.