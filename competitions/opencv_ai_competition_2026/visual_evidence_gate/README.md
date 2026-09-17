# Visual Evidence Gate — OpenCV AI Competition 2026

Operation: `OPENCV26-AGENTIC-VISION-EVIDENCE-GATE-ZSOL-RECOVERY-20260917-0407`  
Recovery owner/finalizer: **Z-Sol / GPT-5.6 Sol**. Preserve the original #15360 source-intent/competition-scout credit; this generation owns recovery after the recorded `INGEST_ERROR PUSH_FAIL`.

## Why this is a competition carrier, not registration theater

The official OpenCV AI Competition 2026 overview/rules currently require every entry to use **OpenCV 5 for substantive image/video analysis** and a **meaningful AWS component**. The optional Agentic Vision path additionally requires visual output to change a later plan, tool call, action, or request for human approval. Its rubric separately values substantive OpenCV/agent integration, appropriate autonomy, task effectiveness/evaluation, and failure handling/observability/security/human control.

Authoritative public sources checked 2026-09-17:
- https://opencv26.devpost.com/
- https://opencv26.devpost.com/rules

This carrier implements that causal chain rather than a chatbot around a fixed detector:

`synthetic scene -> OpenCV perception -> evidence -> policy decision -> optional second OpenCV tool call -> terminal action state`

An amber visual cue changes the next tool call to a targeted ROI recheck. A confirmed warning changes the terminal state to `REQUEST_HUMAN_APPROVAL`. Stale evidence and unsafe action classes fail closed. No physical actuation path exists.

## Source-safe implementation

- `core.py` generates rights-clean synthetic scenes from OpenCV primitives; there are no downloaded images, people, identities, or customer/camera data.
- Full-frame HSV/edge measurements are bounded and deterministic.
- Amber evidence selects a second OpenCV tool call over a bounded ROI; the second measurement can change the final decision.
- Red warning evidence requests human approval; it never produces autonomous physical actuation.
- Evidence older than 30 seconds is `HOLD_STALE_EVIDENCE`.
- Caller requests outside the small safe action-class allowlist are `HOLD_UNSAFE_ACTION_CLASS`.
- Every trace has a canonical SHA-256 receipt and `verify_trace()` exact-recompiles the synthetic generation instead of trusting a caller-authored digest.
- `evaluate_synthetic_suite()` measures expected behavior across clear, warning, ambiguous/recheck, stale, and unsafe-action cases.

## OpenCV 5 truth boundary

Competition mode refuses to run on an OpenCV major version below 5. `--compatibility-mode` exists only so source-development tests can execute in environments that currently ship OpenCV 4.x. Compatibility results are explicitly labeled `LOCAL_SYNTHETIC_SOURCE_DEVELOPMENT_ONLY`; they are not OpenCV 5 submission proof and are not an official score.

Example source-development commands:

```bash
python -m competitions.opencv_ai_competition_2026.visual_evidence_gate run --scenario ambiguous --compatibility-mode
python -m competitions.opencv_ai_competition_2026.visual_evidence_gate evaluate --compatibility-mode
python -m competitions.opencv_ai_competition_2026.visual_evidence_gate aws-plan
```

A competition-final runtime must execute without `--compatibility-mode` under OpenCV 5+ and retain the emitted runtime/version receipt.

## AWS boundary

`aws_boundary.py` is deliberately inactive. It specifies a meaningful target architecture—S3 for rights-cleared input/trace artifacts, a Lambda container for OpenCV 5 perception/policy, and CloudWatch for latency/HOLD/human-control observability—but performs **zero** AWS SDK/network calls and refuses caller-authored deployment evidence. A later owner-authorized deployment needs provider-authenticated evidence binding the account-scoped deployment, exact Lambda image digest containing OpenCV 5+, and execution telemetry for the same generation.

This means source can be reviewed and improved without silently creating spend or mislabeling a design as deployed infrastructure.

## Evaluation / demonstration story

The included deterministic suite is intentionally small but causally meaningful:

1. `clear` -> full-frame perception -> `CONTINUE_MONITORING`.
2. `warning` -> full-frame red evidence -> `REQUEST_HUMAN_APPROVAL`.
3. `ambiguous` -> amber evidence -> **next tool changes** to targeted OpenCV ROI recheck -> confirmed evidence -> `REQUEST_HUMAN_APPROVAL`.
4. `stale_warning` -> stale evidence -> `HOLD_STALE_EVIDENCE`, regardless of visual warning.
5. `unsafe_requested_action` -> visual evidence exists, but a requested autonomous physical action is refused with `HOLD_UNSAFE_ACTION_CLASS`.

The submission demo should show the trace steps side-by-side so judges can see the exact visual measurement that changed orchestration.

## Truth / authority ceiling

This source generation does **not** register for or submit to Devpost, verify entrant eligibility, access an AWS account, deploy infrastructure, spend money, ingest live camera/customer data, actuate a real system, perform surveillance/identity inference, claim an official score/rank, claim a prize/payment, or recognize revenue. Those are separate provider/account actions requiring current owner authority and evidence.
