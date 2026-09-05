# Agent Failure Autopsy — [case reference]

Failure reported: [buyer failure sentence]

Harness and stack: [harness; model if supplied; OS/runtime/tooling if relevant]

Disposition: [DIAGNOSIS_DELIVERED or REFUND_REQUIRED]

## Reconstructed run

List the ordered observed events. End every event with one or more source anchors such as [transcript-1#T1-L03].

First meaningful divergence: identify the earliest observed point where the run left the path needed for the stated outcome, with its anchors.

## Failure chain

Connect the observed events without filling gaps. Keep these as observed facts and cite each step.

## Primary cause

Mark this section as causal inference. State the cause, confidence level, evidence anchors, and confidence rationale.

### Adversarial challenge

For every cause, state at least one plausible competing explanation, cite the evidence used to challenge it, and mark it WEAKENED_BY_EVIDENCE, STILL_PLAUSIBLE, or NOT_TESTED.

## Contributing causes

List only contributing causes supported by the record. Apply the same confidence and adversarial challenge. Say none identified when the artifacts do not support one.

## Fix steps

For each prompt, configuration, or code recommendation:

1. Name the cause it addresses.
2. Give the concrete step.
3. Cite the evidence that supports it.
4. State what the report does not establish.

These are instructions for the buyer. Code implementation is outside this offer.

## Replay or regression-prevention check

State the setup, replay steps, expected result, and exact failure signal. A proposed check is not a claim that it has already passed.

## Limits

Name missing context, untested alternatives, and the effect of redaction on confidence. Do not claim certainty beyond the supplied evidence.

## Fulfillment record

Clock start: [timestamp or not started]

Deadline: [timestamp or not applicable]

Delivered: [timestamp]

Clarification rounds used: [0 or 1]

Human review minutes: [measured value for a buyer delivery]

Automated draft minutes: [measured value when available]

Time measurement purpose: descriptive economics only; never a quality cap

Payment/refund note: [private provider reference remains outside this report]
