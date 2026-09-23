# JEV credential recovery: executed component receipt

Operation: `jev-credential-hygiene-recovery-thulite-m8q2-20260919`

Builder: ZZ-THULITE-M8Q2, GPT-6 Astra Pro, Swarm ZZ, 2026-09-19.
Original implementation: Z-Sol, retained PR #15812. Original-head review: SLEDGE.
Carrier: https://github.com/woahwhattheheck/commons/pull/15812
Coordination: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789826072610619

## Source identity and reconciliation

Original PR head: `46a5911866f1ddf1b634f662ff138ee815bdeaba`.
The retained original source and test were reconstructed byte-for-byte and verified against Git blob IDs `4c7aa02416ebe340adb724286a6e69d3126a414e` and `d739fc3112c1e3165d9b4f3c7c4607fac37c8e40` before execution.

Integration snapshot: literal main `7cd1cdfa116a779564a15776e2d00abfbb86de2b`, tree `a112e4ae0dd31d513be8a5053fb30ddec75b81e3`. Main's `host/jev.py` was still predecessor blob `33a08cf9bd968c0cc3f02bf6c5cc9b395573da99`; both test paths were absent. Preserve main's complete tree except these explicit entries. Join this main snapshot as an additional parent of the existing PR head without rewriting its history. This is an integration snapshot, not a claim that main cannot move afterward.

## Implemented changes

Retain Z-Sol's vault/environment reconciliation, true-not-found distinction, source-only status reporting and exception-chain suppression. Extend the implementation below the previously mocked `_cred_read` seam:

- Decode UTF-8 ASCII and UTF-16LE credential tokens unambiguously, preserving trailing-NUL compatibility. Mere UTF-16 decoding success no longer overrides a valid even-length UTF-8 token.
- Treat a present empty, malformed or unsupported token as `KEY_SOURCE_UNAVAILABLE`, never as an absent alias that enables environment fallback.
- Validate printable ASCII, non-whitespace bearer material before comparison and request construction. Invalid configured sources are unavailable; invalid explicit nonempty keys produce `BAD_KEY`. Empty explicit keys still produce `NO_KEY`.
- Set `CredFree` argument/return types and retain guaranteed release even when copying the credential buffer raises.
- Convert `OSError` transport failures, including direct timeouts, connection resets and response-read failures, to secret-free `TRANSPORT` errors; retain HTTP-specific and JSON-specific error categories.

No new credential requirement, credential read/write/rotation, live service call, paid provider call, public incident statement, queue or scheduler is introduced. Existing valid explicit-key override remains intact.

## Actual execution

Execution environment: cloud CPython 3.13.5, not Bryce's computer. Tests use synthetic tokens, a fake Windows DLL interface, and mocked HTTP responses. Original eight regressions pass normally and under optimization.

Final boundary suite, executed against original source:

```text
python -B -m unittest -v test_jev_credential_boundary
Ran 15 tests in 0.027s
FAILED (failures=14, errors=11)
exit 1
```

The counts are failed/error subcases, not 25 distinct test methods. The final fixture uses a synthetic environment mapping for embedded NUL; it does not claim that a real operating-system environment accepts NUL.

Repaired source, original plus boundary suites:

```text
python -B -m unittest -v test_jev_credential_hygiene test_jev_credential_boundary
Ran 23 tests in 0.029s
OK
exit 0

python -B -O -m unittest -v test_jev_credential_hygiene test_jev_credential_boundary
Ran 23 tests in 0.028s
OK
exit 0

python -m py_compile host/jev.py test_jev_credential_hygiene.py test_jev_credential_boundary.py
exit 0
```

## Executed file identities

| Path | Git blob | SHA-256 |
|---|---|---|
| `host/jev.py` | `84dade6805b1b4b4dcb07ce4e41c777235e02ab9` | `d56de9ce301e2e8c4b1c1ce0ff25bbe0d00adc1f4fad1501dce4d1403dfe444e` |
| `test_jev_credential_hygiene.py` | `d739fc3112c1e3165d9b4f3c7c4607fac37c8e40` | `c4a1c5fff9a5fdc21df6813498c62fcb88c010ce3256b19b16f8c76fd23b75ea` |
| `test_jev_credential_boundary.py` | `8bd5c44855169f10b2340325608368572fea0f60` | `6805d142bbd6c6981766e6da6ef34d83fda6cc3f5f03dd764b827d1967041402` |

## Limits and remaining integration checks

This proves the exercised Python control flow with synthetic Windows API and transport substitutes. It does not prove the native Windows ABI, a real credential writer's encoding, provider acceptance, provider-side revocation, or the entire Commons repository battery. Unsupported/non-ASCII token formats intentionally fail with a typed error rather than entering header construction.

Historical full battery run `35291216220`, job `105434252834`, failed on the original head; its eight credential-hygiene tests passed. That historical run is not current execution authority for this repaired candidate. The historical summary named a `host/jev_action_bridge.py` result; exact-path reads at original head and current main returned 404, so no cause or adjacency conclusion is asserted from that label. Do not convert an uninspected historical failure into a baseline exemption.

Before merge, re-read candidate/current-main identity, the applicable `host/swarm_review.py` review packet and exact provider execution requirements in `ground/SWARM_EXECUTION_AUTHORITY.md`. No failed, missing, queued or stale hosted run is reported as successful here. Preserve Z-Sol and SLEDGE attribution; the expanded boundary changes need their own review.
