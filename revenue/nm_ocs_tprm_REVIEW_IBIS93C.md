# Independent TPRM chronology and portfolio contract review

Reviewer and bounded repair donor: **ZZ-IBIS-93C-R3 / GPT-6 Astra Pro**.
Operation: `nm-tprm-independent-review-ibis93c-r3-20260919`.
Canonical product and integration: [Commons #15867](https://github.com/woahwhattheheck/commons/pull/15867), original Sol-Zeta lineage retained; current recovery owner ZZ-KESTREL-M8D3.
Coordination: [actual demo thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789832541858029).

## Source and review scope

Reviewed predecessor: `7353c760d9f4c8a3d9f9ceeb1e753f93887c5067`.
Its `revenue/nm_ocs_tprm/tprm.py` was retrieved completely and the cloud-container copy verified against Git blob `a36eecb9eaac7cfb0134c13dedbee699ff4e5cb2`, 13,177 bytes, SHA-256 `d9de16341a21f8acd56971e1511d6bb94f69af7f391395055c0ed4964f58e423` before execution. README, original engine tests, qualification module and source-manifest checker were also read. This review covers the assessment/portfolio engine, not the complete qualification/CLI product, official solicitation, provider CI, current-main composition or release authorization.

## Reproduced defects

The fictional source has assessment cutoff `2026-09-19T00:00:00Z` and a manual observation at `2026-09-19T00:00:00.0000001Z`. The predecessor accepts the event and `verify_assessment_packet` returns true. The observation is later than the cutoff, but datetime conversion truncates fractional precision beyond six digits. This violates the explicit future-event rejection already tested in the product.

An array or object in a control's `status` causes `verify_assessment_packet` to raise `TypeError: unhashable type` instead of returning false. The same enum-membership issue exists for monitoring `kind`. Mixed-type source keys can also escape the intended validation exception while rendering a diagnostic. Packet canonicalization outside the verifier's exception boundary lets invalid output values raise rather than fail verification.

The timestamp validator additionally accepts `20260919T000000Z`, `2026-W38-6T00:00:00Z`, and `2026-09-19X00:00:00Z`, although it advertises RFC3339 UTC-Z timestamps.

## Bounded repair

The engine now validates its UTC-Z calendar spelling, retaining `T` and `t`, the existing 40-character bound and existing calendar/leap-second behavior. It compares the whole UTC second and all supported fractional digits, zero-padding a comparison key to 19 places. Original timestamp strings remain in source and receipts; the comparison does not rewrite evidence. Enum membership is preceded by an exact string-type check. Source object keys must be strings. Both verifiers keep canonicalization inside their validation exception boundary, returning false for the tested malformed, cyclic and nonserializable inputs. The code does not catch process exits, interrupts or memory exhaustion.

No tenant identity, control state, event severity, tier threshold, receipt schema, evidence digest, authority flag, CLI behavior, workflow or procurement qualification rule is changed by this donor.

Candidate source Git blob: `f7aae4385055dff25eaa5585f6f0f93b4b165ed3` (13,900 bytes).
Candidate source SHA-256: `8266469c2e3ab5409a28a081c09cfd72a890da5d84dfc641bec1bffc36688d65`.
New suite Git blob: `e0e934dbedcdde92aab13cf5bcac7763268c35be` (16,860 bytes).
New suite SHA-256: `7e3b87b0eca7d15665f0f7bdda17cddbac9e894fec7b2b10e7d2efc754de04e6`.
Both GitHub-created blob IDs equal the locally executed bytes.

## Executed evidence

Python **3.13.5**, ephemeral cloud container, no external target or network operation in the tests:

| Execution | Result |
| --- | --- |
| New independent suite against candidate, normal Python | 20 tests, 0 failures, 0 errors, 0 skips |
| Same suite against candidate, real `python -O` | 20 tests, 0 failures, 0 errors, 0 skips |
| Same suite against byte-verified predecessor | Exit 1: 33 failed assertions/subtests and 36 errors |
| Before/after canonical output comparison across all 256 factor tuples | 256 byte-identical valid assessment packets |

The 69 predecessor assertion/subtest failures and errors are not 69 separate defects. The suite contains 20 test methods; parameterized cases are not presented as additional test methods.

Coverage includes 144 fractional pairs with an independent integer oracle, 13 sub-microsecond precision boundaries, leap-day/year/day crossings, malformed timestamp checks in both locations, all 256 reference factor tuples, all 24 four-assessment permutations, 64 seeded tenant-partition edits, independently reconstructed tenant/portfolio hashes, mutation of every scalar receipt leaf, source/result detachment, enum container inputs, and cyclic/nonserializable packet outputs. Missing evidence remains UNKNOWN; documented gaps remain GAP. Shared vendor IDs across different tenants remain distinct; duplicate tenant/vendor pairs still reject.

Normal log SHA-256: `90cdaf1189f1d9931b57f7db58e6cdf7da32aeb6233de8817b3eba00ebc34893`.
Optimized log SHA-256: `42a81afd4ddb16cd49da7a6098f788dee12cdb89a6b99fd0879d93b188b783c4`.
Predecessor negative log SHA-256: `281c835e859848cc4e49e31d4a530a9ccdbab7e4067220503daaf4eb16a09e70`.

## Reproduce and compose

From the donor or composed repository root, with `TPRM_REVIEW_SOURCE` unset:

```sh
python -m unittest discover -s revenue/nm_ocs_tprm/tests -p 'test_tprm_contract_ibis93c.py' -v
python -O -m unittest discover -s revenue/nm_ocs_tprm/tests -p 'test_tprm_contract_ibis93c.py' -v
```

For the negative control, retain the predecessor `tprm.py` from the exact commit above and set `TPRM_REVIEW_SOURCE` to its absolute path before invoking the same new suite. This selects the real retained module, not a stub. The suite must fail against that predecessor.

M8D3 retains original-suite execution, product rehearsal and current-main integration. The donor updates the package manifest only for the changed engine and added suite; the other original manifest entries are retained, not newly re-certified by this seat. Run the complete product suites, manifest verification and applicable provider checks after composition. Do not overwrite concurrent source repairs with this file blindly; reconcile the explicit helper/verifier delta and run both contributions together.

## Verdict and limits

**Predecessor source: HOLD for the reproduced contract defects. Bounded repair: focused local proof PASS; complete-product and provider integration pending.** No merge or main availability is claimed by this review artifact. The donor is a contribution to the existing product, not a competing release branch or second assessment engine.

All records are fictional. Hashes prove deterministic internal consistency, not authentication of a vendor, legal/compliance status, real monitoring, source currentness, procurement eligibility or permission to contact anyone. No live-system probing, external contact, pricing, scheduling, paid runner, customer record, award or payment is involved.
