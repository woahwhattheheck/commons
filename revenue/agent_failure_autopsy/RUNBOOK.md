# Fulfillment runbook

## 1. Record the intake privately

Create an intake record from the buyer's exact failure sentence, harness and stack name, and redacted artifacts. Use opaque buyer and case references. Keep contact details and the artifact bytes in the private delivery system.

Never request a secret, unredacted credential, production access, or repository access. Ask the buyer to redact tokens, account identifiers, private URLs, and personal data before submission.

## 2. Decide whether the evidence is usable

Usable means the artifacts contain enough stable anchors to describe what happened, connect at least one causal explanation to observed facts, and propose at least one evidence-supported next step.

If one narrow fact is missing, use the single included clarification round. Ask one bundled question and request only another redacted excerpt, log, or screenshot. Add the response as evidence with its own hash and anchors.

If the evidence remains insufficient after that round, stop. Produce a REFUND_REQUIRED report that names the missing causal link without guessing. Do not fill causes or fixes with plausible-sounding findings.

## 3. Start the clock from evidence arrival

For a usable intake, clock_basis_evidence_ids names the artifacts that made the case usable. usable_evidence_at must equal the latest received_at time among those artifacts. The deadline is the same local wall-clock time on the next Monday through Friday. Any holiday adjustment must be agreed and recorded before the clock starts.

The validator derives the weekday deadline and rejects a different timestamp.

## 4. Draft from evidence anchors

An automated peer may prepare a PEER_DRAFT. Every timeline event, failure-chain step, cause, and fix must cite an evidence reference in the form evidence-id#anchor-id. A fix must also name the cause IDs it addresses.

Confidence labels describe the support in this case:

- HIGH: the supplied evidence directly shows the claimed mechanism and a materially different explanation conflicts with the record.
- MEDIUM: the evidence supports the mechanism, but one or more plausible alternatives remain untested.
- LOW: the mechanism is a bounded hypothesis that explains the record but needs a named replay check.

Confidence is not certainty. The rationale must state why the label fits and name material alternatives when they remain.

## 5. Review and measure

A PEER_DRAFT cannot be delivered. A human operator reviews the exact report against the supplied evidence, removes unsupported findings, and marks the record HUMAN_REVIEWED.

Record active human-review minutes separately from automated drafting. The current ceiling of 15 minutes is an UNMEASURED_TARGET, not an achieved claim. Each buyer record reports whether that individual review was at or below the target. Aggregate claims require actual delivery data.

## 6. Deliver one of two outcomes

DIAGNOSIS_DELIVERED requires:

- a nonempty evidence-linked timeline and failure chain;
- at least one primary cause, with any contributing causes separated;
- confidence and rationale for each cause;
- concrete supported fix steps aimed at named causes;
- one replay or regression-prevention check;
- human review and measured operator time;
- delivery by the recorded one-business-day deadline.

REFUND_REQUIRED applies only after the included clarification round when the evidence is still insufficient. It must contain no diagnosis or fix claims. Initiate the USD 29 refund in the official payment system and record the private provider receipt there. No payment URL or refund is created by this repository package.

## 7. Buyer-facing format

Use report-template.md to render the validated JSON record into plain language. Keep source anchors beside each conclusion. State limitations and untested alternatives. Do not promise implementation or certainty.
