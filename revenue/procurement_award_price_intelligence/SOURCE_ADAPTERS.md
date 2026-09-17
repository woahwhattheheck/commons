# Procurement award source adapters

Operation: `PROCUREMENT-AWARD-SOURCE-INGEST-ADAPTERS-20260916-ZSOL`  
Issue: `#15128`

This layer turns retained, explicitly structured public-procurement source payloads into the exact input consumed by `engine.py`. It exists so award, bid-tabulation, executed-contract, and amendment/option evidence can be ingested reproducibly instead of hand-normalized before each price review.

## Truth boundary

`source_adapters.py` is a **parser and evidence-preservation layer, not a provider authenticator**.

The request carries retained source metadata: URI, raw-source SHA-256, observed time, authority classification, source class, and title. The adapter:

- preserves that metadata exactly;
- verifies that `payload_sha256` matches the canonical structured payload it actually parsed;
- never upgrades `SECONDARY_INDEX`, `SELF_AUTHORED`, or `SYNTHETIC_FIXTURE` to `BUYER_OFFICIAL`;
- records `source_provider_authenticated=false` and `buyer_officialness_authenticated=false`;
- feeds normalized bytes into the landed price-intelligence compiler, which still applies stale/conflict/comparability rules.

A caller can lie about a URI or authority label. This module does not make the label cryptographically or provider-authenticated. Production use therefore requires the upstream source-capture process to retain and review the actual public buyer source. The adapter receipt proves deterministic transformation of the supplied generation; it does not prove that a buyer published it.

## Supported shapes

### `AWARD_NOTICE_JSON_V1`

Compatible source classes: `AWARD_NOTICE`, `BOARD_AWARD`.

Required explicit fields: opportunity ID, award ID, vendor, amount in minor units, currency, basis, unit, term months, award date. The observation is `AWARD`. Missing amount, missing term, or contradictory basis/unit semantics produce HOLD records and no price observation.

### `BID_TABULATION_JSON_V1`

Compatible source class: `BID_TABULATION`.

The document fixes opportunity/tabulation identity, currency, basis, unit, term, and bid date. Each row must have a row ID, vendor, bid amount in minor units (or `null` when not explicit), and a real JSON boolean `responsive`. Only responsive rows with explicit amounts and complete basis/unit/term semantics become `BID` observations. Nonresponsive or ambiguous rows remain auditable HOLDs.

### `EXECUTED_CONTRACT_JSON_V1`

Compatible source class: `EXECUTED_CONTRACT`.

An explicit base contract amount becomes an `AWARD` observation. A separately explicit option amount is **never added to the base**: it is retained as an `OPTION` observation and marked `OPTION_NON_ANCHOR`, so the price engine cannot silently treat potential option value as current award price.

### `AMENDMENT_OPTION_JSON_V1`

Compatible source class: `AMENDMENT`.

Explicit amendment or option values are retained as `OPTION` observations only. They are never promoted to `AWARD`, even when buyer-official. This prevents a change order, exercise, or amendment delta from being treated as the original comparable award.

## Hold-not-guess rules

The adapter does not infer a money value from text, a unit from a rate, a term from dates, base value by subtracting options, total value by adding base and options, responsiveness from rank, award status from bid position, currency conversion, or buyer-officialness from an HTTPS hostname.

Representative HOLD codes are `AMBIGUOUS_AMOUNT`, `MISSING_TERM`, `MISSING_RATE_UNIT`, `UNEXPECTED_LUMP_UNIT`, `NONRESPONSIVE_BID_EXCLUDED`, `OPTION_TERM_MISSING`, `OPTION_NON_ANCHOR`, `CHANGE_RECORD_NON_ANCHOR`, and `SOURCE_NOT_BUYER_OFFICIAL`.

Malformed structure, duplicate JSON keys, non-integer JSON numbers, bool-as-money, duplicate source/row IDs, bad hashes, HTTP/credentialed URIs, incompatible source classes, and payload-hash mismatches fail closed.

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

The existing path-scoped `procurement-award-price-intelligence.yml` workflow runs both the original engine suite and the adapter suite in normal and optimized Python. No extra runner matrix is added.