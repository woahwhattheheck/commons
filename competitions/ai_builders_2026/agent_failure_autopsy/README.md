# Agent Failure Autopsy · AI Builders Hackathon 2026

**Tagline:** Evidence-linked diagnosis for one failed coding-agent run.

Agent Failure Autopsy turns a messy failed Codex / Claude Code / coding-agent run into a bounded, auditable diagnostic workflow: reconstruct the run, locate the first meaningful divergence, rank primary and contributing causes with calibrated confidence, challenge plausible alternatives, prescribe evidence-supported fix steps, and require a replay/regression check.

This entry wraps the existing public `revenue/agent_failure_autopsy/**` product without modifying or reminting its fulfillment contract, schemas, offer, Stripe identifiers, or checkout. The commercial package was built during the AI Builders hackathon period (the public package and checkout funnel were already present by September 5–9, 2026). This competition work adds a judgeable local product surface and submission materials.

## Why this is an AI product

Coding agents fail in ways that ordinary stack traces do not explain: the first visible error may occur long after the first reasoning/tool divergence; the same symptom can have several plausible causes; and an LLM can confidently invent causality when the evidence is incomplete. The product treats AI diagnosis as a **reviewable evidence workflow**, not a free-form answer.

The AI/agent role is to synthesize a candidate autopsy from the bounded evidence set. The fulfillment contract forces that draft to carry evidence links, confidence, competing hypotheses, fix steps, and a regression-prevention check. Automated output remains `PEER_DRAFT` until a separate capable reviewer confirms the exact report against the exact evidence. That review boundary is a feature: it targets hallucination risk directly.

## Working demo

From repository root:

```bash
python competitions/ai_builders_2026/agent_failure_autopsy/demo_server.py --check
python -m unittest competitions.ai_builders_2026.agent_failure_autopsy.test_demo_server
python competitions/ai_builders_2026/agent_failure_autopsy/demo_server.py
# open http://127.0.0.1:8765
```

The demo does not fake a new case. It runs the existing public synthetic intake/report through the same `revenue/agent_failure_autopsy/fulfillment.py validate` command documented by the commercial product, then exposes the intake, report, validator receipt, and truth boundary in a local browser UI.

No buyer data, secrets, model/provider calls, payment action, or external side effect are used by the demo.

## Product architecture

```text
sanitized failed run
        |
        v
 bounded intake contract
        |
        v
 AI / agent candidate autopsy
 run reconstruction
 first divergence
 primary + contributing causes
 alternative-hypothesis challenge
 fix + regression check
        |
        v
 evidence-link / schema / timing validator
        |
        +---- invalid or unsupported ----> clarification / refund path
        |
        v
 PEER_DRAFT
        |
        v
 independent capable reviewer
        |
        v
 buyer-ready diagnostic
```

The public repository contains only synthetic material. Real buyer artifacts remain in an owner-private delivery system and are not committed.

## What is differentiated

1. **First-divergence focus.** The report asks where the run first became wrong, not merely which final exception appeared.
2. **Adversarial diagnosis.** Plausible alternative causes must be challenged rather than silently discarded.
3. **Evidence-linked claims.** Findings are only useful when a reviewer can trace them back to supplied artifacts.
4. **Hard intake bounds.** One failed run, at most ten files, 25 MB raw, and two million extracted Unicode characters.
5. **Human/peer review is explicit.** Automated output cannot silently promote itself to buyer-ready truth.
6. **Commercially real.** The underlying product has an existing live USD 29 checkout, while this competition wrapper makes no sale/payment claim.

## Existing product boundary

Read-only dependencies for this entry:

- `revenue/agent_failure_autopsy/fulfillment.py`
- `revenue/agent_failure_autopsy/intake.schema.json`
- `revenue/agent_failure_autopsy/report.schema.json`
- `revenue/agent_failure_autopsy/examples/**`
- `revenue/agent_failure_autopsy/RUNBOOK.md`
- `revenue/agent_failure_autopsy/offer.json`

The competition wrapper intentionally does **not** edit those paths.

## Submission package

- `SUBMISSION.md` — copy-ready Devpost description and technical story.
- `DECK.md` — ten-slide presentation content.
- `DEMO_SCRIPT.md` — four-minute demo/video runbook.
- `READINESS.json` — fail-closed record of what is complete vs external/human pending.
- `demo_server.py` — loopback-only working judge demo.
- `test_demo_server.py` — exact synthetic integration tests.

## Truth / authority boundary

This repository work does not assert Devpost registration, Discord membership, a recorded video, contest submission, judging, prize, buyer acceptance, sale, payment, cash, or revenue. Those are separate external states. `READINESS.json` keeps them false/null until independently completed.

Operation: `AI-BUILDERS-AGENT-FAILURE-AUTOPSY-ZMCK7P9-20260913`  
Owner/finalizer: `Z-MobiusCrown-914022-K7P9` (`ZMC-K7P9`) / GPT-5.6 Sol.
