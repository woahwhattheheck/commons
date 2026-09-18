# Live-pursuit gap → partner-capability shortlist

Operation: `LIVE-PURSUIT-GAP-TO-PARTNER-SHORTLIST-20260916-ZSOL`

This offline compiler turns source-bound mandatory pursuit requirements into a deterministic evidence crosswalk and a **capability/proof/workshare requirement shortlist**. It never recommends a company or contact route.

## Mechanical states

Every retained requirement compiles to exactly one of:

- `PASS` — current retained TJLabs evidence matches the repository trust generation.
- `PRIME_SUPPORTED` — current retained prime evidence matches the repository trust generation.
- `PARTNER_REQUIRED` — mandatory, uncovered, and explicitly partner-eligible.
- `OWNER_INPUT` — stale, ambiguous, missing, conflicting, unsupported, or unsafe to map.

For `CERTIFICATION`, `REFERENCE`, `SLA`, `SECURITY`, and `LEGAL`, generic capability prose cannot promote the requirement. Explicitly mapped stale/unverified/conflicting evidence forces `OWNER_INPUT`; unrelated prime evidence cannot wash it away.

## Retained trust generation

The compiler initializes from `trusted_evidence_manifest.json` and checks the committed source files against their retained SHA-256 values. The current generation is `SYNTHETIC_ONLY`: it supports the mechanics fixture but does not establish LIVE qualification evidence.

Synthetic `as_of` is historical fixture time. LIVE currentness uses a process UTC clock captured during initialization. The trust-generation digest and currentness basis are retained in the compiled evidence.

## Live truth boundary

`materialization_mode=LIVE` currently fails closed with the exact state:

`LIVE_MATERIALIZATION_BLOCKED_NO_VERIFIED_CARRIER_SET`

The issue contract requires a verified current 5–10-pursuit carrier set **present on main** before live materialization can be asserted. Caller-supplied `verified_carrier_set` rows are retained as candidate/audit evidence only; they cannot authenticate their own presence on main and cannot clear the blocker. A later integration may consume a separately retained, code-owned/main-bound carrier manifest and then explicitly widen this boundary. Until that integration exists, synthetic fixtures may exercise mechanics but cannot assert live pursuit truth.

Shortlist entries always emit:

- `company: UNASSIGNED`
- `route: UNASSIGNED`

No partner recommendation, email/contact, buyer/portal mutation, bid/submission/signature, price commitment, qualification invention, award, payment, or revenue authority is created.

## Determinism and verifier

The compiler canonicalizes unordered inputs, writes:

- `canonical_input.json`
- `crosswalk.json`
- `shortlist.md`
- `receipt.json`

The receipt binds canonical input, crosswalk, shortlist, Markdown bytes, status, and blockers with SHA-256. `verify` recompiles from source input and byte-compares all four outputs. Writes are create-exclusive and use `O_NOFOLLOW` when available.

## Retained CI

Commons has a bounded active-workflow budget. This product therefore does not consume a dedicated workflow slot. Root bridge `test_live_pursuit_partner_shortlist.py` is discovered by the existing retained `tests` battery and runs the nested suite under normal and real `python -O`, plus a real CLI compile→verify round trip. `source-parses` also wakes on the Python carrier.

## Run

```bash
rm -rf /tmp/partner-shortlist
python revenue/live_pursuit_partner_shortlist/compiler.py compile \
  --input revenue/live_pursuit_partner_shortlist/fixtures/pursuits.synthetic.json \
  --out-dir /tmp/partner-shortlist
python revenue/live_pursuit_partner_shortlist/compiler.py verify \
  --input revenue/live_pursuit_partner_shortlist/fixtures/pursuits.synthetic.json \
  --out-dir /tmp/partner-shortlist
python -m unittest discover -s revenue/live_pursuit_partner_shortlist/tests -p 'test_*.py' -v
python -O -m unittest discover -s revenue/live_pursuit_partner_shortlist/tests -p 'test_*.py' -v
python test_live_pursuit_partner_shortlist.py -v
```

The runtime is stdlib-only and performs no network calls.
