# Operator runbook — $29 Agent Failure Autopsy

Use this only after a real purchase event or for the explicitly synthetic sample.

1. **Payment fence.** Read the existing payment provider receipt. Store only its SHA-256 digest in the input. Never paste card, customer, bank, checkout-session, or private provider data. If no provider receipt is verified, leave the case `UNVERIFIED`; the compiler will hold it.
2. **Sanitization fence.** Reject credentials, tokens, private URLs, customer records, PII/PHI, unrelated incidents, archives/executables/repository dumps, and over-cap evidence. The public contract allows at most 10 files / 25 MB raw / roughly 500k text tokens cumulatively.
3. **Case brief.** Copy only the intended outcome, observed failure, stack, first useful error, and digest-only evidence metadata into strict JSON. Do not store filenames if they contain private facts.
4. **Compile.** Run `core.py compile INPUT NEW_OUTPUT_DIR`. The directory must be new. Read `report.md`; do not change the derived state by hand.
5. **Analyze only when READY.** `READY_FOR_ANALYSIS` means the operator asserted verified payment and the sanitized intake is complete. It does not prove provider authentication, cash availability, or revenue recognition.
6. **Clarification/refund.** One clarification is included by the public contract. If a defensible diagnosis still cannot be produced, set a bounded sanitized `refund_reason`. A refund is not satisfied until either the provider payment state is `REFUNDED` or a refund receipt SHA-256 is recorded. This package never executes the refund.
7. **Delivery.** After sending the actual diagnosis through the owner-approved channel, hash the exact delivered artifact and set `delivery_receipt_sha256`; recompile. `DELIVERED` is artifact evidence only, not evidence of cash settlement.
8. **Reorder/upsell.** Point the buyer to the existing public offer pages only when context supports it. Never mark an upsell accepted in this package.

No email, Stripe, refund, buyer-contact, cash, accounting, or revenue authority exists in this code.
