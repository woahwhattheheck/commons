# Submission outline — Visual Evidence Gate

**Status:** SOURCE CARRIER ONLY — NOT SUBMITTED — AWS DEPLOYMENT UNKNOWN

## Problem

Vision systems often jump from a model output straight to an action. That makes it hard to prove which visual evidence changed the system's behavior, and it creates a bad failure mode when evidence is stale or ambiguous.

## Solution

Visual Evidence Gate makes the perception-to-action link explicit and reproducible. OpenCV measures a synthetic scene, the agent policy consumes only bounded evidence, and that evidence chooses the next operation. Ambiguous amber evidence triggers a targeted OpenCV recheck; confirmed warning evidence stops at a human approval request. Unsafe requested action classes and stale evidence fail closed.

## Why it is agentic

The visual result is not the end product. It changes orchestration:

- no actionable cue -> monitor;
- ambiguous cue -> call a second OpenCV perception tool on a bounded ROI;
- confirmed warning -> request human approval;
- stale/unsafe state -> HOLD.

The trace records every perception, decision, selected next tool, and terminal state in a canonical receipt.

## Evaluation

The source suite exercises five deterministic scenarios and reports exact expected-vs-observed terminal states plus per-trace receipts. A final entry should add rights-cleared held-out imagery/video and report task-level precision/recall or success metrics without overwriting the synthetic regression suite.

## AWS story to implement before submission

Target architecture:
1. S3 object event provides a rights-cleared input generation.
2. Lambda container runs OpenCV 5+ and the deterministic evidence/policy loop.
3. Trace artifacts are retained in S3 by content digest.
4. CloudWatch records latency, HOLD reason counts, and human-control requests.

The current repository carrier performs none of those provider actions. Final submission claims must be backed by provider evidence for the exact deployed image/runtime generation.

## Responsible operation

- no face recognition, identity inference, or surveillance classification;
- no production physical actuation;
- explicit human-control state for warnings;
- stale/malformed evidence holds;
- deterministic receipts expose why orchestration changed;
- synthetic rights-clean development fixtures only in this generation.

## Demo script

1. Run `clear`; show `CONTINUE_MONITORING`.
2. Run `ambiguous`; highlight the amber fraction and the selected `opencv_targeted_roi_recheck` tool call.
3. Show the second perception step and final `REQUEST_HUMAN_APPROVAL`.
4. Run `stale_warning`; show that freshness beats apparent urgency and the system holds.
5. Run `unsafe_requested_action`; show the hard refusal of autonomous physical actuation.
6. Verify a trace, then tamper one measurement and show verification fail.
7. Display the inactive AWS plan and clearly separate source evidence from future provider deployment proof.
