# BidVeil threat model

## Protected data

Private claim values, contractor subject secret, source evidence bytes/digests, issuer-specific source relationships, and any identity mapping behind the subject secret are private by default.

## Public by design

Opportunity ID/generation, normalized public requirements, evaluation time, opportunity/requirement digests, opportunity-scoped subject commitment, opportunity-scoped nullifier, requirement IDs, coarse result states, and receipt digest.

## Adversaries and controls

| Threat | Control | Prototype status |
|---|---|---|
| Replay one profile into a different opportunity | opportunity digest enters subject commitment + nullifier | tested |
| Replay a proof for same opportunity | stable opportunity nullifier; Compact scaffold adds requirement-level spent set | local derivation tested; chain enforcement not run |
| Rewrite threshold/allowlist after proof | entire normalized opportunity generation is SHA-256 bound | tested |
| Inject stale/expired evidence | canonical UTC + explicit expiry + max-age checks | tested |
| Backdate/future evidence | future observation => HOLD | tested |
| Claim from untrusted issuer | closed issuer allowlist => HOLD | tested |
| Type confusion (`true` as `1`, float money) | booleans rejected as integers; JSON floats rejected | tested |
| Duplicate IDs / ambiguous JSON | duplicate requirement/claim/JSON keys rejected | tested |
| Add undeclared claim | profile becomes HOLD_UNKNOWN_CLAIMS | tested |
| Tamper public receipt | receipt SHA-256 integrity gate | tested |
| Infer private values from receipt | only IDs/statuses exposed; fixture-value leak test | tested structurally |
| Treat local hash as ZK proof | hard-coded mode + `onchain_proof_verified=false` | tested/visible |
| Caller chooses an easier on-chain predicate | **blocker:** Compact scaffold does not yet bind public predicate definition to requirement digest | unresolved; must close before deployment |
| Cross-runtime hash mismatch | do not equate SHA-256 JSON with Compact persistentHash | fenced, test vectors required |

## Authority ceiling

A local `QUALIFIED` receipt means only: *given these private source inputs and this exact public opportunity, the deterministic local predicate engine returned satisfied*. It is not issuer authentication, legal/compliance status, buyer acceptance, a contract award, a chain proof, or cash.
