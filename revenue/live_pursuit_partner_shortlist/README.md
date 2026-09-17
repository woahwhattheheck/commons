# Live-pursuit gap → partner-capability shortlist

Operation: `LIVE-PURSUIT-GAP-TO-PARTNER-SHORTLIST-20260916-ZSOL`

This offline compiler turns source-bound mandatory pursuit requirements into a deterministic evidence crosswalk and a **capability/proof/workshare requirement shortlist**. It never recommends a company or contact route.

## Mechanical states

Every retained requirement compiles to exactly one of:

- `PASS` — current verified TJLabs-owned evidence exactly covers it.
- `PRIME_SUPPORTED` — current verified retained prime-side evidence exactly covers it.
- `PARTNER_REQUIRED` — mandatory, uncovered, and explicitly partner-eligible.
- `OWNER_INPUT` — stale, ambiguous, missing, conflicting, unsupported, or unsafe to map.

For `CERTIFICATION`, `REFERENCE`, `SLA`, `SECURITY`, and `LEGAL`, generic capability prose cannot promote the requirement. Explicitly mapped stale/unverified/conflicting evidence forces `OWNER_INPUT`; unrelated prime evidence cannot wash it away.

## Live truth boundary

`materialization_mode=LIVE` is blocked with the exact state:

`LIVE_MATERIALIZATION_BLOCKED_NO_VERIFIED_CARRIER_SET`

unless the input contains a current, verified 5–10-pursuit carrier set and every compiled pursuit is represented in that set. The bundled fixture is deliberately `SYNTHETIC`; it exercises mechanics and asserts no live pursuit truth.

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
```

The runtime is stdlib-only and performs no network calls.
