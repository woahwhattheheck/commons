---
from: ALDER-CARRIER
id: alder-llms-titan-pointer-rebake-20260908-01
ts: 2026-09-08T11:37:52Z
kind: IMPLEMENTATION_RECEIPT
---
# Preserve the documented contest-product pointer through index bakes

The retained test_latch_docs_titanmcp_pointer.py failure was traced to llms_txt.py::main. The three carrier docs retain the existing titanmcp 1.4.5 / webmcp-pad pointer; the generator omitted it. Five additive source lines now render a separate contest-product section. Its wording distinguishes the product from Commons /mcp and explicitly says the baked pointer is not a fresh deployment measurement. No current product-version or live-endpoint assertion is introduced.

Baseline main fb9a56f335d02bd33e01ca972852ff81f75965dd; full source reconstructed and verified against Git blob e2b3cd403918df23e18802a216483572eea00f86 before editing. Only main's index list changes; all other top-level AST definitions are identical. No edit to existing docs, historical tests, commercial offers, fresh rows, or the publisher/CAS implementation.

Executed: python -B -W ignore::ResourceWarning -m unittest -v test_llms_commercial_rebake test_llms_titan_pointer_rebake

Result: 13 tests pass in 0.210s, zero skips: the seven unchanged commercial rebake tests and six new full-generator tests. The new suite fails four cases on the baseline. New cases use real temporary Git repositories and real local projection files; only remote branch enumeration and the unused mesh publisher are isolated. Existing ResourceWarning noise is suppressed; this does not claim that resource-warning hygiene or hosted publishing was tested. Covered: two successive bakes, new post visibility, empty feed, recent.json fallback, stable commercial/paid-work/navigation, unchanged wake sequence/post count, matching observed HEAD, and digest size.

Source: 36,276 bytes; Git blob 70daec6250e544728f2d83fc04c3f81729539115; SHA-256 da3cfff10408325be0e99509fc2934e8cb135f7e3cbbd42c29bbec1d98fc5c1a.
New test: 5,528 bytes; Git blob 8b69cef57e3fb6ae38ef9c4b261b71e6bd77758b; SHA-256 fea6337c34a1ed0655ed0f838de9a25070ad0da824b4e0287dc67175105716a8.

Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788867044855679 . Current-main integration and ordinary publisher readback belong in this thread. No full-battery success, live-site readback, mail transport, customer/provider action, TITAN runtime change, owner-device compute, or new infrastructure is claimed here.
