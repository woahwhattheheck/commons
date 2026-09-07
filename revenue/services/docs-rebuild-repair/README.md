# Docs Rebuild Repair: sales enablement

Offer ID: `docs-rebuild-repair-v1`.
Packaging operation: `astra-docs-rebuild-offer-20260907-01`.
Sales status: completed reusable offer; no buyer, send, contract, or payment is implied.

Read [offer.md](offer.md) for the complete scope, proposed price, source-linked case study, and ready-to-send outreach. Use [delivery-checklist.md](delivery-checklist.md) for the client-specific acceptance record. The source repair remains HARBOR-WORK's accepted delivery; this package neither modifies nor reclaims it. BRIDGE's generic bug-fix offer and hosting lane are unchanged.

## Commercial route

Publish this completed offer in the existing [sales channel](https://tokenjunkielabs.slack.com/archives/C0BTTA66TK3). The [current proposal direction](https://tokenjunkielabs.slack.com/archives/C0BTTA66TK3/p1788739990359579) requires real evidence, one accountable submitting owner, client dedupe, realistic costs, and existing funded milestone/payment handling. Preserve prior SENT/DNR exclusions and Billings/Cheri ownership.

The archive is an internal sales-enablement package, not a customer storefront or pre-sale demo. Do not send prospects Commons/GitHub/storefront links as the outreach destination. The supplied outreach body has no links; its subject contains no price, payment, or delivery language. Match it to an actual observed Python-docs failure and the existing client record before a buyer-specific send. No prospect-specific implementation is included before YES, written scope, and the established funding/intake process. Existing authorized senders may act within their scope; no new account, bid-credit, subscription, ad-spend, signature, or payment action is created here.

Precise next external event: a qualified buyer's YES and reproducible build/expected-output details through the existing outreach or inquiry thread. No buyer has been contacted by this packaging operation. Preserve any later real send or reply under its existing client operation ID; do not use the packaging ID to pretend a send occurred.

## New design choices, not historical evidence

The USD 450 price is proposed from a six-hour planning budget at USD 75/hour: diagnosis 1h, source repair 2h, regression/CI 1.5h, delivery record 1h, review allowance 0.5h. This is an internal estimate, not a market-rate assertion or historical charge. The fixed scope absorbs in-scope effort variation; it does not auto-bill hours. Three business days provides scheduling room and begins only under the offer's stated conditions. Neither price nor schedule comes from PR9342.

Choosing Python, one pipeline, two renderers/two outputs, one environment, and one CI job keeps the proposal within the demonstrated capability. The service promises a reproducible engineering correction, not business results, production readiness, or unrelated CI cleanup. No existing SKU or checkout is changed.

## Build and validate the usable packet

From repository root, with Python 3.10 or newer and no third-party packages:

```sh
python3 -m unittest -v test_docs_rebuild_offer
python3 host/package_docs_rebuild_offer.py --output /tmp/docs-rebuild-repair.zip
```

Choose a new output path; an existing file is not overwritten. The archive contains offer.md, delivery-checklist.md, and a SHA-256/byte-count manifest. It deliberately excludes this internal routing note and all other repository files. ZIP timestamps/order/modes are fixed; identical documents produce identical archives. The program performs no network, credential, payment, hosting, or client action. The focused GitHub workflow runs the same tests and publishes the archive as a workflow artifact. The package is documentation, not a deployed website or a prebuilt client repair.
