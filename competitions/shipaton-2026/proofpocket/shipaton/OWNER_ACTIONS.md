# Owner/provider gates — do not mark complete without evidence

Source is not the submission. To cross the Shipaton gate without inventing state:

1. Complete/confirm the RevenueCat account email verification.
2. Confirm an eligible Android developer account (Google Play or Samsung Galaxy Store) with authority to publish a **new** app.
3. Create the Android app record for exact package `com.tokenjunkielabs.proofpocket` and upload a signed release/closed-test build as the store requires.
4. In RevenueCat, bind the exact store app, create a product/package/offering, attach it to entitlement **`pro`**, and supply the app's **public** SDK key at build time.
5. Exercise purchase + restore on a supported real store/test path; record observed entitlement behavior. Do not use a local boolean as purchase proof.
6. Publish the first public ProofPocket store version inside the Shipaton eligibility window and before **2026-09-30 23:45 PDT / 2026-10-01 06:45 UTC**; capture the public U.S.-available store URL.
7. Capture an app icon and screenshot; record a <2-minute demo showing the app, local digest/receipt workflow, verification/tamper rejection, and actual RevenueCat purchase/restore path.
8. Complete Devpost registration/submission and terms under the authorized owner identity.
9. Write a separate external witness JSON containing the observed package/version, observation time, verified gates, store URL, demo URL, screenshot evidence, and Devpost submission observation. Run `readiness.py --witness ...`.

Never commit signing keys, provider secrets, bank/card data, store passwords, or private RevenueCat API keys.
