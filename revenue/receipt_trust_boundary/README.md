# Receipt trust boundary

A self-contained SHA-256 is an **integrity checksum**, not an authenticity root.
Anyone who can rewrite a JSON receipt can also rewrite its contents and recompute the
checksum. This package makes that distinction executable for Commons revenue and
evidence artifacts.

The rule is not new. TITAN PR #13471 already established the same trust boundary for
an action-divergence witness: the report's self-hash was insufficient, so validation
required an out-of-band frozen report commitment. Independent review of revenue PR
#13657 then exposed the same failure class in a commercial receipt verifier: arbitrary
semantics could be self-digested and reported as valid. This package extracts the
existing trust law into a reusable, provider-free primitive; it does not replace or
modify either owner's source lane.

## Three deliberately different operations

`inspect` verifies only the receipt's own `receipt_sha256`. A matching result is named
`INTEGRITY_ONLY`. The output explicitly keeps external commitment, semantic contract,
source authenticity, buyer acceptance, payment, and recognized revenue false.

`bind` additionally requires a lowercase SHA-256 supplied **outside the receipt** with
`--expected-receipt-sha256`. PASS means only that the receipt is stable relative to
that caller-supplied trust root. The tool cannot know whether the caller got that value
from a trusted prior Slack publication, signed log, release manifest, buyer-controlled
system, or from the attacker; `source_authenticity_verified` therefore remains false.

`verify` also requires a semantic contract whose canonical SHA-256 is independently
supplied with `--expected-contract-sha256`. The contract can freeze exact top-level
keys and type-sensitive `equals` / `in` rules. PASS means the externally committed
receipt conforms to the externally committed contract. It still does **not** prove
that the source facts are authentic, that a buyer accepted anything, that a contract
was executed, that payment occurred, or that revenue is recognized.

This is intentionally a composition primitive: product-specific code must establish
its own source provenance and business/legal authority. A receipt verifier must never
manufacture those authorities merely because hashes line up.

## CLI

```sh
python -m revenue.receipt_trust_boundary inspect receipt.json

python -m revenue.receipt_trust_boundary bind receipt.json \
  --expected-receipt-sha256 "$PUBLISHED_RECEIPT_SHA256"

python -m revenue.receipt_trust_boundary verify receipt.json \
  --expected-receipt-sha256 "$PUBLISHED_RECEIPT_SHA256" \
  --contract revenue/receipt_trust_boundary/example_contract.json \
  --expected-contract-sha256 "$PINNED_CONTRACT_SHA256"
```

Inputs must be ordinary regular files; symlinked inputs are rejected. JSON parsing
rejects duplicate keys and non-finite numbers. Rule equality is canonical/type-sensitive,
so Python's `True == 1` alias cannot satisfy an integer rule and `1` cannot satisfy a
`1.0` rule.

## Contract v1

A contract has exactly five top-level keys:

- `schema`: `receipt-trust-boundary/contract-v1`
- `contract_id`: non-empty stable identifier
- `required_top_level_keys`: keys that must exist on the receipt
- `allowed_top_level_keys`: complete allowed receipt surface; must include
  `receipt_sha256`
- `rules`: non-empty list of object-path `equals` or `in` rules

Both the receipt commitment and contract commitment are explicit caller inputs. A
contract stored next to a forged receipt and trusted merely because it hashes itself
would recreate the same failure at a different layer.

## Threat boundary

This package defeats post-publication self-rehash forgery **only when** the expected
commitments came from a trust root established before the disputed evidence changed.
It does not provide signatures, identity, timestamping, source-system attestation,
or buyer authority. If those are required, bind a real signature / trusted log /
buyer-controlled receipt at the integration layer rather than relabeling a checksum.
