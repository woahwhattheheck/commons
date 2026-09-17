# Multi-photo packet quality and custody

This is an additive successor layer for the canonical OpenCV 2026 Visual Evidence Gate. It does not replace `visual_gate.py`, claim a second competition entry, or authorize any physical/business action.

The existing gate answers: **what did this retained frame measure, and how may that evidence change a bounded later plan?** This layer answers a different prerequisite question for multi-photo inspection packets: **is the packet itself complete, readable, non-duplicative, and byte-bound enough to reach human review?**

## Bounded actions

OpenCV measurements compile to one code-owned next step:

- `HOLD_UNSAFE_OR_UNREADABLE` for decode/dimension failures;
- `HOLD_DUPLICATE_EVIDENCE` when two required slots are filled by exact or perceptual near-duplicates;
- `REQUEST_MISSING_VIEW` for an absent required slot;
- `REQUEST_RECAPTURE` for measured low focus or severe shadow/highlight clipping;
- `ACCEPT_FOR_HUMAN_REVIEW` only when the packet clears those evidence-quality gates.

`ACCEPT_FOR_HUMAN_REVIEW` is not claim approval, compliance, fraud proof, payment approval, or any other substantive decision.

## Measurements and custody

`packet_quality.py` binds each image to SHA-256 and measures decoded dimensions, Laplacian focus variance, clipping fractions, mean luminance, dHash and a downsampled visual descriptor. Filenames, EXIF and prose cannot override measured bytes. The artifact binds the packet, thresholds, measurements and bounded next action to a deterministic receipt; verification recompiles exactly.

`aws_packet_quality.py` is read-only. Its manifest must exactly bind bucket, canonical S3 keys, ETags, the packet image set and payload digests. The outer runtime envelope is included in a separate deterministic receipt and its verifier recompiles the entire adapter artifact. There is no arbitrary URL fetch or write path.

The optional Lambda-shaped entry point refuses a competition-ready posture unless OpenCV 5.x is imported and `AWS_EXECUTION_ENV` exists. Even then, generated artifacts keep AWS execution/submission/prize/revenue authority false; real provider evidence must be retained separately.

## Truth ceiling

This layer never proves or authorizes external action, claim/payment approval, fraud/compliance findings, AWS deployment/execution, Devpost submission, prize/award/payment, or revenue. The retained authoring/runtime proof on OpenCV 4.13 is source-development evidence only; the competition's OpenCV 5 and meaningful-AWS requirements remain external until actually exercised.
