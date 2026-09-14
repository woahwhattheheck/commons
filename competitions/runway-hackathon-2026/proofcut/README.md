# ProofCut

**Evidence-bound product demo compilation for the Runway Hackathon 2026.**

ProofCut takes a bounded software-release evidence packet and produces a deterministic demo shot manifest. Factual claims are tied to content-addressed evidence. Runway-generated media is allowed only in explicitly marked connective slots and cannot silently substitute for proof of product behavior.

## Why
AI can make demos more expressive, but it can also fabricate capabilities. ProofCut makes that boundary machine-checkable.

## Local proof (no network, no spend)

```bash
python -m unittest discover -s tests -v
python -m proofcut.cli compile examples/release.json
python -m proofcut.cli render-plan examples/release.json --provider fake
python -m proofcut.cli demo examples/release.json --output proofcut-demo.html
python tools/release_gate.py
```

The `demo` command emits a deterministic, dependency-free judge surface: evidence cards, generative HOLD boundaries, and the canonical manifest/receipt. It performs no media generation.

## Real Runway execution

Real generation is intentionally not the default:

```bash
pip install '.[runway]'
export RUNWAYML_API_SECRET='...'
python -m proofcut.cli render-plan examples/release.json \
  --provider runway --execute --max-credits 100
```

The adapter uses WAN 3.0 with a deterministic preflight estimate. Current official pricing used by this carrier: 480p 5 credits/sec, 720p 10, 1080p 20; supported WAN 3.0 duration 2–30 sec. Re-check provider docs before event-day use.

No API key, acceptance, attendance, provider output, submission, award or payout is claimed by this repository.
