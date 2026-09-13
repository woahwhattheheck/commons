# Devpost submission copy

## Project name
Agent Failure Autopsy

## Tagline
Evidence-linked diagnosis for one failed coding-agent run.

## Inspiration
Coding agents increasingly write, test, deploy, browse, and call tools across real software workflows. When one fails, the final exception is often the least interesting part. The expensive question is: **where did the run first diverge from the intended path, what evidence supports that diagnosis, what alternative explanation still fits, and what should we change so the same failure cannot recur?**

A free-form LLM answer is not enough for that job. A model can tell a convincing story from incomplete logs. Agent Failure Autopsy was built to make AI diagnosis reviewable.

## What it does
A buyer or operator supplies one bounded, sanitized failed run. The workflow turns it into an evidence-linked autopsy containing:

- a reconstruction of the run;
- the first meaningful divergence;
- primary and contributing causes with calibrated confidence;
- explicit evidence references for each material finding;
- an adversarial challenge of plausible alternative causes;
- concrete fix steps supported by the evidence; and
- a replay/regression-prevention check.

The product's key safety property is promotion control: automated analysis is `PEER_DRAFT`. It cannot become buyer-ready merely because a model sounds certain. A separate capable reviewer must inspect the exact report against the exact evidence and remove unsupported claims.

## How we built it
The core product is a Python fulfillment/verification package with JSON-schema contracts for intake and report records, a bounded public synthetic case, an operational runbook, and an existing commercial offer. This hackathon wrapper adds a local judge UI that exercises the exact synthetic case through the real public validator rather than mocking the workflow.

The local demo uses only Python's standard library. `demo_server.py --check` calls the existing fulfillment validator. The browser UI then shows the retained synthetic intake, synthetic report, validator result, and truth/authority boundary. No buyer artifacts or external provider calls are involved.

The workflow is intentionally hybrid:

1. bounded sanitized evidence enters the case;
2. an AI/coding-agent seat produces a candidate autopsy;
3. deterministic validation checks the report/evidence contract;
4. invalid or unsupported cases route to clarification/refund rather than forced certainty;
5. a distinct capable reviewer checks the exact draft before buyer-ready delivery.

This lets AI do the synthesis work it is good at without letting generation erase provenance or review.

## What makes it different
Most agent observability products help you see traces. Agent Failure Autopsy is about **closing the causal loop after a failed run**. It treats the diagnosis itself as an artifact that needs evidence, alternative-hypothesis pressure, and a regression check.

It also has a deliberately small commercial unit: one failed run. The bounded scope keeps the promise concrete and makes refund behavior explicit when the evidence cannot support a defensible answer.

## Challenges we ran into
The hardest design problem was preventing the diagnostic workflow from quietly upgrading uncertain model output into truth. We addressed that with several explicit boundaries:

- instructions embedded in supplied evidence are untrusted data;
- actual customer artifacts never belong in the public repository;
- automatic output remains `PEER_DRAFT`;
- evidence size/count boundaries are fixed;
- every material finding must remain reviewable against evidence;
- a deadline never justifies inventing a diagnosis; and
- a failed/unsupported case can route to clarification or refund.

The hackathon demo adds another boundary: it is a loopback-only judge surface over public synthetic data. It does not claim a real sale, payment, review, or buyer outcome.

## Accomplishments we're proud of
- A real fulfillment contract instead of a concept-only chatbot.
- A public synthetic case that can be validated end-to-end.
- Explicit adversarial challenge of plausible alternative diagnoses.
- A promotion gate separating automated draft from reviewed delivery.
- Bounded one-run economics and an existing USD 29 checkout without pretending that a checkout link is revenue.
- A demo that executes the production validator rather than replacing it with presentation-only logic.

## What we learned
The failure mode in AI debugging is often not lack of intelligence; it is **unpriced uncertainty**. If a model is allowed to collapse uncertainty into a polished paragraph, the operator loses the distinction between observation, inference, and speculation. Requiring evidence links, alternatives, and independent review makes the final diagnosis slower than a one-shot answer but much more useful for real operations.

We also learned that a commercially useful AI product can be narrow. One run, one autopsy, one clarification round, one reviewed report is easier to trust and buy than an unlimited promise to “fix your agents.”

## What's next
- add provider-neutral adapters that can ingest sanitized exports from more coding-agent harnesses without expanding authority;
- make the evidence graph easier to inspect visually;
- measure repeated failure classes across opt-in, privacy-safe aggregate cases;
- add regression templates for common agent/tool boundary failures; and
- validate whether the USD 29 entry point converts into larger implementation work without changing the autopsy's bounded promise.

## Technologies
Python, JSON Schema, local HTTP demo surface, coding-agent/LLM-assisted analysis workflow, evidence-link validation, peer/human review gates.

## Public repository
`https://github.com/woahwhattheheck/commons/tree/main/competitions/ai_builders_2026/agent_failure_autopsy`

## Working demo command

```bash
python competitions/ai_builders_2026/agent_failure_autopsy/demo_server.py --check
python competitions/ai_builders_2026/agent_failure_autopsy/demo_server.py
```

Then open `http://127.0.0.1:8765`.

## External completion still required
Devpost registration/submission, the hackathon's mandatory Discord participation, and a recorded 3–5 minute demo video are external owner/browser actions. This repository does not represent any of those as complete until they actually are.
