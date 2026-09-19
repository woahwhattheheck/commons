# Partner-shortlist recovery: executed source and replay

Operation: `LIVE-PURSUIT-GAP-TO-PARTNER-SHORTLIST-20260916-ZSOL`.
Recovery/reviewer: ZZ-HARBORGLASS / GPT-6 Astra Pro, September 19, 2026.
Original Z-Sol design/source, ZOV-0445 recovery/tests and predecessor reviewer defect credit are preserved.

This record covers the executable source retained at PR #15699 head `141b373f9e3d43b667a9396e50470f831b7962a8`. It is independent cloud-container execution, not GitHub Actions execution, a main-merge receipt, or real pursuit qualification. The fixtures are explicitly synthetic.

## Exact executable closure

All nine files were reconstructed from connected GitHub reads and matched to their actual Git object hashes before execution. Python 3.13.5 / Linux; no compiler stub, substituted trust generation, network invocation, paid executor or owner-PC execution.

| Repository path | Git blob |
|---|---|
| `revenue/live_pursuit_partner_shortlist/compiler.py` | `e99388aa50ff7ac6276cd3799a92d05777cc679c` |
| `revenue/live_pursuit_partner_shortlist/trusted_generation.py` | `0b2a7a851e8c564bd9d30ccee6530ad099089df2` |
| `revenue/live_pursuit_partner_shortlist/trusted_evidence_manifest.json` | `2920d662b9dc13c49dc249cbcff667c06a61ca55` |
| `revenue/live_pursuit_partner_shortlist/fixtures/pursuits.synthetic.json` | `867b4d3077a15eb757c7e7e3fad9bc9f9720f353` |
| `revenue/live_pursuit_partner_shortlist/fixtures/source-a.json` | `3203a2732675d1470831c9c7bdef0e852c16170f` |
| `revenue/live_pursuit_partner_shortlist/fixtures/e1.json` | `fc79bc08144c8a064ee9777c6f10bac7d13fa409` |
| `revenue/live_pursuit_partner_shortlist/fixtures/e2.json` | `fd9760268162171781644ddc4030ed7a46ba2596` |
| `revenue/live_pursuit_partner_shortlist/tests/test_compiler.py` | `04c015431013f10897ae23d000aa1fd145273605` |
| `test_live_pursuit_partner_shortlist.py` | `0246419192d74dec8e622d2b93992e71e7b38747` |

Compiler SHA-256: `1eec3ae12231b21ec3b503a7ebef0ed8275372270b6e994084ce5a6e9fbc443c`.

## Actual test execution

Commands below ran from the reconstructed repository root. Every process returned zero; no tests were skipped.

```text
python -m unittest discover -s revenue/live_pursuit_partner_shortlist/tests -v
Ran 25 tests in 2.090s
OK

python -O -m unittest discover -s revenue/live_pursuit_partner_shortlist/tests -v
Ran 25 tests in 0.590s
OK

python -m unittest -v test_live_pursuit_partner_shortlist.py
Ran 3 tests in 3.730s
OK

python -O -m unittest -v test_live_pursuit_partner_shortlist.py
Ran 3 tests in 3.657s
OK
```

Each three-test root bridge itself runs the full normal and optimized nested suite plus a real CLI compile/verify round trip. Do not count those as three additional independent product cases or inflate repeated executions into distinct coverage.

The actual tests cover retained source/digest/owner/requirement mapping, sensitive evidence categories, duplicate handling, deterministic ordering and deduplication, overwrite refusal, output tamper, the saved-compiler classifier-rebind predecessor, synthetic-to-live promotion, caller-clock rollback and all-false external authority.

## Worked synthetic replay

At `2026-09-19T14:40:40Z`, both normal and optimized CLI invocations returned:

```text
COMPILE_OK status=OWNER_REVIEW_READY requirements=3 shortlist=1
VERIFY_OK
```

This status describes the **synthetic mechanics fixture**, not current commercial readiness. R1 is `PASS`, R2 is `PARTNER_REQUIRED`, and R3 is `PRIME_SUPPORTED`. The one missing capability is a public-sector reference; company and contact route remain `UNASSIGNED`.

All four generated files were byte-identical between normal and optimized execution:

| File | SHA-256 |
|---|---|
| `canonical_input.json` | `f84a521f40ce456a8fde6aac6bcd0e8e7d96bbd3cd836feeda0ed6085e4766eb` |
| `crosswalk.json` | `f176f308ca12af9fbb7fe4e8a501a8bdd74f26375639b7e084ecdfc12d03fab5` |
| `receipt.json` | `c152d910d981186e5b5beb4298d7addfcd646bd2557c4b4a721c4ede22ecb87b` |
| `shortlist.md` | `cee8edb92ae68f4c3212a769b1ec7d14198c83b0cce3103212316c39dc92104c` |

Changing only the fixture mode to LIVE was also executed: status remained `LIVE_MATERIALIZATION_BLOCKED_NO_VERIFIED_CARRIER_SET`, all three requirement rows remained `OWNER_INPUT`, and every external authority bit was exact false. No live five-to-ten-pursuit carrier set is established by this test.

Reproduce from a complete checkout, using a fresh output directory rather than deleting an existing path:

```sh
OUT=$(mktemp -d)
python revenue/live_pursuit_partner_shortlist/compiler.py compile \
  --input revenue/live_pursuit_partner_shortlist/fixtures/pursuits.synthetic.json \
  --out-dir "$OUT"
python revenue/live_pursuit_partner_shortlist/compiler.py verify \
  --input revenue/live_pursuit_partner_shortlist/fixtures/pursuits.synthetic.json \
  --out-dir "$OUT"
```

Repeat with real `python -O` and a different fresh directory to compare the four output hashes. The normal and optimized unit commands above retain negative and tamper cases.

## Integration boundary

The old source head's Actions results were reread as terminal, not inferred from its outdated queued description: `35296816250` tests, `35296816196` source-parses and `35296816360` workflow-surface reported failure; open-door, path-manifest and muhlnickel-spec guards reported success. These are historical provider results for that exact head, not results for a recomposed head.

Current-main composition must retain the full base tree and overlay only this product, its root bridge, this record, and the two existing product wake-path additions in `tests.yml`. At examined main `e468cafe1adb382e772858297aa6f0cedfbbac7f`, the product subtree and root bridge were absent, while the unmodified `tests.yml` blob was still `57d36525209d661b3c3d5121a58dc7e6861a4d60`, identical to the old PR base. Thus the retained workflow blob `34916a2198c6223f586e3f43332894fca8e8f9a2` adds only the two reviewed wake paths; no workflow slot or other job change is introduced.

Fresh provider execution and the live main/head binding required by `ground/SWARM_EXECUTION_AUTHORITY.md` remain distinct from this source proof. Consult the current PR for the actual integration state. This report creates no partner selection, outreach, scheduling, bid, price, signature, payment or revenue authority.
