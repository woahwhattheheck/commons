# Agent Failure Autopsy — [case reference]

Failure reported: [buyer failure sentence]

Harness and stack: [harness; model if supplied; OS/runtime/tooling if relevant]

Disposition: [DIAGNOSIS_DELIVERED or REFUND_REQUIRED]

## What happened

List the ordered events. End every event with one or more source anchors such as [transcript-1#T1-L03].

## Failure chain

Connect the observed events without filling gaps. Each step must cite the supplied evidence.

## Primary cause

State the cause, confidence level, evidence anchors, confidence rationale, and any plausible alternative that remains untested.

## Contributing causes

List only contributing causes supported by the record. Say none identified when the artifacts do not support one.

## Fix steps

For each prompt, configuration, or code change:

1. Name the cause it addresses.
2. Give the concrete step.
3. Cite the evidence that supports it.
4. State what the report does not establish.

These are instructions for the buyer. Code implementation is outside this offer.

## Replay or regression-prevention check

State the setup, replay steps, expected result, and exact failure signal. A proposed check is not a claim that it has already passed.

## Limits

Name missing context, untested alternatives, and the effect of redaction on confidence.

## Fulfillment record

Clock start: [timestamp or not started]

Deadline: [timestamp or not applicable]

Delivered: [timestamp]

Clarification rounds used: [0 or 1]

Human review: [measured minutes for a buyer delivery]

15-minute review target: [AT_OR_BELOW, ABOVE, or NOT_ASSESSED]

Payment/refund note: [private provider reference remains outside this report]
