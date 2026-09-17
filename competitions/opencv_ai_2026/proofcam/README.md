# ProofCam — Agentic Visual Evidence Triage

ProofCam is a human-bounded OpenCV evidence-control surface for inspection, delivery, worksite, claims, and other photo packets. It is being built as a reusable product and as a candidate foundation for the **OpenCV AI Competition 2026, powered by AWS**.

The important behavior is not “AI looked at an image.” OpenCV measurements change the next allowed action in a deterministic perception → decision/action loop:

- unreadable/unsafe bytes → `HOLD_UNSAFE_OR_UNREADABLE`
- exact or perceptual near-duplicate evidence across required views → `HOLD_DUPLICATE_EVIDENCE`
- absent required view → `REQUEST_MISSING_VIEW`
- measured blur or clipping → `REQUEST_RECAPTURE`
- packet that clears those evidence gates → `ACCEPT_FOR_HUMAN_REVIEW`

`ACCEPT_FOR_HUMAN_REVIEW` is deliberately **not** claim approval, payment approval, compliance, fraud detection, or any other business decision.

## Measured facts

The core uses OpenCV to decode bytes and computes dimensions, Laplacian focus variance, shadow/highlight clipping fractions, mean luminance, 64-bit difference hash, and a downsampled visual descriptor digest. Caller filenames, EXIF, labels, and prose do not override those measured facts.

Each packet binds payload SHA-256 values. The compiled artifact binds the packet, measurements, code-owned thresholds, the exact next action, reasons, and a semantic receipt. Verification is deterministic recompile rather than trusting a detached receipt.

## AWS boundary

`aws_adapter.py` is a **read-only S3 manifest adapter**. It accepts only a bucket, canonical manifest key, and exact ETag; the manifest must exactly bind the image set, object keys/ETags, and payload digests. It has no arbitrary URL fetch and no write path.

The optional `lambda_handler` refuses a live competition posture unless the imported OpenCV runtime reports major version 5 and `AWS_EXECUTION_ENV` is present. Even then, its artifact does not self-mint proof of AWS deployment: provider/runtime evidence must be retained separately.

No source in this carrier joins Devpost, creates AWS resources, spends money, submits an entry, or claims a prize.

## Authority ceiling

Every artifact hard-codes false for:

- external action authorization
- claim approval
- payment authorization
- fraud proof
- compliance proof
- AWS execution proof
- competition submission proof
- prize proof
- recognized revenue

This keeps a visual-evidence tool from silently becoming an autonomous adjudicator.

## Competition truth

Current public rules require substantive OpenCV 5 image/video analysis and a meaningful AWS component for a final entry. The separate Agentic Vision rubric rewards OpenCV output that changes a later plan/tool/action or human-approval request, plus task evaluation, failure handling, observability, security, and human control. Those external requirements are **not** proven merely because this repository contains compatible source.
