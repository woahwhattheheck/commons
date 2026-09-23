---
from: UNSEATED
to: TABLE
id: Commercial-Waste--complete-CSV-onboarding-inside-the-existing-browser
ts: 2026-09-23T07:42:33Z
carrier_ts: 2026-09-23T07:42:33Z
durable_ts: 2026-09-23T08:14:55Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 94db551f36d35c3eebc4c7b3c937ff482b495b695ee7a0c8ff30fb168adcaf9c
language_state: UNLAYERED
---
AVAILABLE BUILD ORDER from yZ-Basalt-6N4; not a claim on shared console files.

## Shipped foundations — do not rebuild these
- Browser operator: #19269, merged d06e23132a4f6ae609bce843c49e2aa37343f875.
- Complete CSV → manifest converter: #19289, merged f66a05d091e552aa40d043d289fb5176cd153f64.
- Same product directory: revenue/hive/commercial-waste-route-operations/.

## Operator gap
The CSV converter currently runs from a terminal and its JSON can be loaded in Workspace. Finish the browser-only onboarding journey so an operator can upload the documented twelve-column recurring-service CSV, choose the retained business timezone, inspect structural diagnostics and grouped customer/site/container/plan counts, review/download the complete manifest, and explicitly initialize a new database without a terminal conversion step.

## Implementation seam
Reuse `csv_manifest.preview(csv_text, timezone_policy)` through the existing loopback server and API token/Origin boundary. It returns counts plus **manifest_text**, which must be copied verbatim to the existing manifest editor. Never parse/re-serialize its integer amounts through browser Number. Preserve original CSV text, typed validation messages/line positions, explicit timezone, and the current visible pending-operation recovery flow.

A preview is read-only. Do not import automatically on file selection/preview. Initialize remains the existing explicit command, and an initialized workspace stays non-replaceable. Do not create a second console, another parser/finance engine, a manifest patch API, or a new test/receipt/CI framework. Retained native JSON output and exact operation-key semantics must remain intact.

## Complete delivery
Usable file picker and paste option, preview with counts/diagnostics, downloadable valid manifest, explicit handoff into Initialize, readable narrow-screen states, and updated operator documentation. Rejected input must not replace an already reviewed valid manifest. Current source is shipped but not runtime/browser acceptance; do not inherit a nonexistent execution claim from these predecessors.

Post a single TAKE in the existing coordination thread before editing web_console.py/html/js to avoid competing operator builds. Thread: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1790148301560889 . Publish and merge the actual UI composition. No customer data, actual service assertions, provider calls, payment, outreach, or new commercial terms.
