# ProofPocket — RevenueCat Shipaton 2026 carrier

ProofPocket is a new Android-first, offline work-evidence app: create a project, state a bounded completion claim, attach local files, hash them on-device, and export a deterministic content-addressed receipt. Anyone with the JSON receipt can import it and detect changed claims/evidence without trusting a ProofPocket server.

## Product boundary

- **Local-first:** evidence bytes stay on the device. ProofPocket stores only local project metadata and SHA-256 digests.
- **Free:** up to 3 local projects, JSON receipt creation/export/import verification.
- **Pro:** an observed active RevenueCat `pro` entitlement unlocks unlimited local projects and platform-native PDF proof packs.
- **Fail closed:** no RevenueCat public SDK key means Pro stays locked. SDK errors never create entitlement truth. Store/submission readiness is compiled separately and cannot be minted from source state.

## Android build

Current pinned build inputs were checked against vendor docs on 2026-09-13:

- AGP `9.4.0`, `compileSdk/targetSdk 37`, minSdk 26.
- RevenueCat Android SDK `10.15.1`.

Supply the **public** RevenueCat SDK key only at build time (never a secret API key):

```bash
./gradlew :app:assembleDebug -PPROOFPOCKET_REVENUECAT_PUBLIC_SDK_KEY=goog_xxx
```

This repository intentionally does not contain the key, RevenueCat products/offerings, store credentials, signing keys, or a claim that purchases have been tested.

## Local proof engine tests

The receipt engine and entitlement fail-closed policy are plain Kotlin and can be tested without Android tooling:

```bash
kotlinc \
  app/src/main/java/com/tokenjunkielabs/proofpocket/core/ReceiptEngine.kt \
  app/src/main/java/com/tokenjunkielabs/proofpocket/core/EntitlementPolicy.kt \
  core-tests/CoreTests.kt -include-runtime -d /tmp/proofpocket-core-tests.jar
java -jar /tmp/proofpocket-core-tests.jar
python3 -m unittest discover -s tests -v
python3 shipaton/readiness.py shipaton/manifest.json --json  # expected HOLD until external witness exists
```

## Receipt semantics

`receiptId = SHA256(canonical_payload_json)`. Evidence is sorted by stable evidence ID before hashing, so input order does not change identity. Evidence IDs derive from content SHA-256. Duplicate IDs, malformed digests/timestamps, negative sizes, and unsupported schemas are rejected. Import verification rebuilds the canonical payload and compares the digest.

This is **tamper evidence**, not a claim of signer identity or a digital signature. A PDF proof pack contains the same receipt ID and digest excerpts; it does not claim cryptographic signing.

## Competition truth

`shipaton/readiness.py` requires an external witness separate from `manifest.json`. The current checked-in manifest is intentionally `HOLD` because RevenueCat account/product verification, store developer access/publication, demo media, and Devpost submission are not presently evidenced in this lane. See `shipaton/OWNER_ACTIONS.md`.
