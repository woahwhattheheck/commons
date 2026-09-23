# Framer source generation: operator and integration notes

**Usable result:** the existing pursuit and workshare commands now describe the recovered source bundle without pretending that buyer documents supplied bidder credentials, a price, a partner commitment or permission to act. The two evaluators consume the same retained generation, not independent copies of policy or commercial truth.

## Run and inspect

```sh
P=opportunities/invest_appalachia_framer_lms
python "$P/carrier.py"
python "$P/workshare.py" --current-packet "$P/current_packet.json" --workshare "$P/partner_workshare.json"
```

The pursuit receipt reports recovered buyer sources, incomplete bidder responses, nine unverified/missing qualification gates, unverified U.S.-prime eligibility, `PRIME_HOLD`, an unpriced proposal and `proposal_budget_within_cap=false`. The workshare receipt reports that same generation plus **$24,000 / PROPOSED_NOT_ACCEPTED / unresolved $60,000-cap integration / no acceptance, receivable or revenue**. Every external-authority field is false. The observed deterministic outputs are retained in [source_generation_execution.json](source_generation_execution.json).

A successful process exit means only “the input is this retained internal snapshot.” It is not a release signal, source-currentness assertion, bid authorization or positive business decision. Missing and unpriced evidence is a normal result of the valid retained snapshot.

## API and file contract

```python
from opportunities.invest_appalachia_framer_lms import carrier, workshare
from pathlib import Path

root = Path("opportunities/invest_appalachia_framer_lms")
packet = carrier.load_json(root / "current_packet.json")
offer = workshare.load_json(root / "partner_workshare.json")
requirements = carrier.load_json(root / "requirements.json")
manifest = carrier.load_json(root / "source_generation.json")

pursuit = carrier.evaluate(packet, requirements, manifest)
commercial = workshare.evaluate(packet, offer, requirements, manifest)
```

The last two parameters are optional on both evaluator APIs. Omission loads sibling `requirements.json` and `source_generation.json` relative to the module, not the caller's working directory. Explicit values must be parsed JSON from the same generation. Both CLIs accept `--requirements` and `--source-manifest` to select those files. `carrier.py` also accepts `--current-packet`; its default is its sibling packet. Workshare preserves its two required packet/offer flags.

`normalize` validates the complete pursuit generation. `validate_workshare` and `validate_qualification_generation` are component validators retained for compatibility; call `evaluate` when a receipt bound to the full source bundle is required. The two complete evaluators reject a mismatched manifest or requirements object even when the packet and offer themselves are unchanged.

## One-way generation graph

| Object | Canonical SHA-256 |
|---|---|
| `source_generation.json` | `a70c78c77a7084ef9cf1499f0e7831e2031d4e635405c8955df25b57c6f01093` |
| `requirements.json` | `5d012da1612cb220cfe0d7c4c02c47175a726bad1254855240c24afa6926ef66` |
| `current_packet.json` | `79e1bfc46617239e1c05b4c22e97e4d6672743103041e2b6b7b3e71bd6d1b30d` |
| `partner_workshare.json` | `33548cdf0b30a664b847eeea0eb6ad6d7a06b2a8d35ddfa91be0953d1f564636` |

The manifest identifies reviewed buyer inputs and the old packet/workshare generation. Requirements bind the manifest and encode source/evidence distinctions. The packet binds both manifest and requirements. The offer binds that packet and the same source pair. Both implementations capture their expected generation at import. The graph has no self-hash or cyclic digest.

Canonical JSON uses UTF-8, sorted object keys, compact separators and `allow_nan=False`; array order is significant. JSON loaders reject duplicate keys, non-finite values, malformed UTF-8 and unpaired surrogates. Receipt digests cover the receipt without its own `receipt_sha256` field. Git blob IDs in the execution record identify exact source bytes and are a separate hash convention.

Post-import replacement of public compatibility constants and validators does not replace the nested evaluator's captured semantics. This is consistency protection for a trusted in-process library, **not a sandbox against arbitrary code execution or monkeypatching every Python primitive**. Source hashes bind recorded identities, not remote bytes that were freshly fetched during evaluation. No network verification is implied.

## Try a real rejected mix without editing the checkout

```sh
P=opportunities/invest_appalachia_framer_lms
TMP=$(mktemp -d)
printf '{}\n' > "$TMP/mixed-requirements.json"
python "$P/carrier.py" --requirements "$TMP/mixed-requirements.json"
# Expected: exit 2, a requirements-generation diagnostic on stderr,
# and no receipt on stdout. The repository files remain unchanged.
```

The operator may remove that disposable directory separately. The executable regression suite creates and cleans its own temporary directories, invokes the real script/module commands with timeouts, checks stderr/stdout/exit codes, and confirms the six shipped source/data files are not rewritten. Optimized test execution passes `-O` to child Python processes as well.

## Preparing a later genuine evidence or pricing generation

Retain the historical manifest and this execution record. Review new buyer source identities separately from private bidder evidence. Update only the qualification records supported by actual retained evidence; an unfilled role is still not named work history. Prepare an actual priced Attachment C across all six categories and recurring costs, and separately document a selected platform and any accepted workshare.

Rebuild in graph order: new source manifest, requirements, packet, offer, then both evaluators' expected digests. Review source interpretations, notes, price semantics, response-completeness meaning and external-action fields together. Run the focused normal/optimized suites and update expectations only for justified changes. Do not edit a digest merely to make a caller-supplied change pass. Future authorization remains a separate real instruction; the existence of a newer valid generation alone grants none.

## Retained evidence and limits

The 25 new tests add whole-predecessor digest conservation, optional-template semantics, explicit source bindings, all-nine buyer-URL promotion refusals, true/zero/string/null authority mutations, public binding isolation, deterministic receipts and real CLI failures. The original eight workshare tests are unchanged. The original ten carrier tests retain their behavior checks; one expected source-status value changes and the separate incomplete-response assertion is added.

These tests establish behavior for the retained internal generation. They do not establish bidder qualifications, correctness of any LMS product, current insurance, staffing capacity, live source availability, an accepted partner, buyer approval, hosted workflow success or main merge state. The publication and independent-review receipts belong on #16383 and the original demo thread, not inside a fabricated business approval.
