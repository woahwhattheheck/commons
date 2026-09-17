# Diagnostic upsell evidence ladder

This package turns a **completed diagnostic's retained verified findings** into an **owner-review list of bounded follow-on offers**. It is a commercial-truth compiler, not generic cross-sell copy and not an outbound sender.

The compiler does not invent an offer because a diagnostic happened. It needs two independent source-shaped inputs:

1. a completed diagnostic with exact source product/version/digest, buyer-authorized finding classes, retained finding evidence/currentness, contradiction state, and unresolved holds; and
2. a current offer catalog with generation/source digests, currentness window, explicit eligible source products, finding-class applicability, bounded scope, acceptance criteria, exclusions, effort band, copied catalog price, and commercial state `PROPOSED_NOT_ACCEPTED`.

A candidate exists only when a **current catalog row explicitly matches a current verified delivered finding** and the source product is eligible. Every surfaced candidate retains the exact finding/evidence references and the exact offer source reference/digest. Multiple candidates remain multiple owner-review candidates; priority only makes output deterministic and does not accept or select one.

## States

The output is exactly one of:

- `OWNER_REVIEW_UPSELL_CANDIDATE` — one or more current source-bound offers explicitly match verified delivered findings.
- `NO_NEXT_STEP` — evidence is good, but no current offer explicitly matches. This is the anti-generic-cross-sell state.
- `HOLD_EVIDENCE_INSUFFICIENT` — delivered finding evidence is partial, unknown, stale, or absent.
- `HOLD_UNRESOLVED_BLOCKER` — the diagnostic retains an open blocking hold.
- `HOLD_SCOPE_CONTRADICTION` — a delivered in-scope finding is explicitly contradicted.
- `HOLD_CATALOG_INVALID` — the offer catalog is outside its currentness window.
- `HOLD_SOURCE_DRIFT` — the catalog generation predates the completed diagnostic, so it cannot establish current follow-on truth.

Structural source errors (unknown fields, duplicate keys/IDs, future evidence, malformed digests, finding classes outside buyer-authorized diagnostic scope, non-integer money, unsupported commercial state, etc.) fail the compile instead of becoming a candidate.

## Authority ceiling

Every packet keeps these false: external/buyer contact, buyer acceptance, contract/change acceptance, invoice creation/send, payment-link or payment-request authority, provider mutation, customer-result or savings claims, accounting recognition, cash, and revenue claims.

A candidate's commercial state is always `PROPOSED_NOT_ACCEPTED` and its selection authority is always `OWNER_REVIEW_ONLY`. This package never emails, DMs, posts forms, touches Stripe/banks/providers, or calls Muse. A later outbound operation is separate and must use the existing coordination/single-writer process.

`source_authentication` is deliberately `RETAINED_DIGEST_REFERENCE_NOT_PROVIDER_AUTHENTICATED`: source refs/digests preserve lineage, but this compiler does not pretend it authenticated a remote provider.

## Inputs

`example_diagnostic.json` and `example_catalog.json` are **synthetic reference fixtures for schema/demo use only**. They are not a live customer, live acceptance, or a claim that their repeated placeholder SHA-256 values authenticate current Commons bytes. In production, build the catalog from current retained commercial sources and exact source digests (for Commons, examples include the verified product/service surfaces referenced by `revenue/OFFERING_FAMILIES.md`, `commerce.html`, and the specific product page).

The catalog is intentionally an input rather than hard-coded Python. New current offers can become eligible by producing a new source-bound catalog generation; stale or withdrawn offers can stop surfacing without a code release.

## Run the reference rehearsal

From the Commons repository root:

```bash
tmp="$(mktemp -d)"
python -m revenue.diagnostic_upsell_evidence_ladder.ladder compile \
  --diagnostic revenue/diagnostic_upsell_evidence_ladder/example_diagnostic.json \
  --catalog revenue/diagnostic_upsell_evidence_ladder/example_catalog.json \
  --out "$tmp/packet.json" \
  --markdown "$tmp/packet.md"

python -m revenue.diagnostic_upsell_evidence_ladder.ladder verify \
  --diagnostic revenue/diagnostic_upsell_evidence_ladder/example_diagnostic.json \
  --catalog revenue/diagnostic_upsell_evidence_ladder/example_catalog.json \
  --packet "$tmp/packet.json"

cat "$tmp/packet.md"
```

Expected compile state for the synthetic fixture:

```text
OWNER_REVIEW_UPSELL_CANDIDATE
```

Expected verifier result while the evidence/catalog remain current:

```text
VERIFIED
```

The CLI accepts strict UTF-8 JSON only, rejects duplicate keys, floating-point/non-finite JSON, unknown schema fields, and symlink/non-regular inputs where the platform exposes `O_NOFOLLOW`. Output is create-exclusive: a packet path is never silently overwritten.

## Semantic verification

`verify` does more than re-hash the packet. It:

1. validates the packet receipt;
2. recompiles from the diagnostic and catalog at the packet's bound evaluation time and byte-compares the semantic result; and
3. if the old packet exposed an upsell candidate, recompiles at **verification time** so expired evidence/catalog truth cannot remain green merely because an old receipt still hashes.

Thus an attacker cannot edit a price/scope, recalculate the outer receipt, and turn self-authored commercial text into a verified candidate.

## Tests

```bash
python -m py_compile \
  revenue/diagnostic_upsell_evidence_ladder/ladder.py \
  tests/test_diagnostic_upsell_evidence_ladder.py
python -m unittest -v tests.test_diagnostic_upsell_evidence_ladder
python -O -m unittest -v tests.test_diagnostic_upsell_evidence_ladder
```

The hostile suite covers no-match anti-cross-sell behavior, source-product mismatch, partial/stale evidence, contradiction, blocking holds, catalog expiry, catalog generation older than delivery, withdrawn offers, scope-class escape, non-proposed commercial state, bool/float money, duplicate JSON keys, unknown fields, packet/receipt tamper, recomputed-receipt semantic tamper, replay after catalog expiry, deterministic candidate ordering, create-exclusive CLI output, and symlink input refusal.
