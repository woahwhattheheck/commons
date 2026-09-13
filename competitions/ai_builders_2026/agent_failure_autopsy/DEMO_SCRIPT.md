# Four-minute demo / video script

## 0:00–0:30 — Problem
Show the title page.

> Coding agents fail in layers. The final exception may be five steps downstream from the first wrong tool call or bad assumption. Agent Failure Autopsy takes one failed run and turns it into an evidence-linked causal report instead of another free-form guess.

Point out: one run, bounded evidence, first divergence, alternatives, regression check.

## 0:30–1:00 — Architecture
Show `DECK.md` slide 4 or the README architecture.

> The model does synthesis, but it does not get to declare itself correct. Sanitized evidence enters a bounded intake. An AI seat drafts the run reconstruction and diagnosis. Deterministic checks enforce the report/evidence contract. The result remains PEER_DRAFT until a separate capable reviewer inspects the exact report against the exact evidence.

Mention that instructions embedded in evidence are untrusted data.

## 1:00–1:20 — Start the working demo
From repository root:

```bash
python competitions/ai_builders_2026/agent_failure_autopsy/demo_server.py --check
python competitions/ai_builders_2026/agent_failure_autopsy/demo_server.py
```

Open `http://127.0.0.1:8765`.

> This is deliberately local and provider-free. I am going to run the public synthetic case through the same validator used by the fulfillment package. There is no buyer data and no mocked success API.

## 1:20–2:30 — Run the synthetic autopsy
Click **Run the public synthetic case**.

Show the validator receipt first.

> The check invokes `revenue/agent_failure_autopsy/fulfillment.py validate` on the checked-in synthetic intake and report. A pass means the synthetic report satisfies the public fulfillment contract. It does not mean a buyer paid us or that a human reviewed it.

Scroll to the truth boundary and call out false values for buyer data, payment, sale, human review, and external action authority.

Then show the synthetic intake and report.

> The important product idea is that the diagnosis remains inspectable. A reviewer can walk from a causal claim back to evidence, see confidence, inspect alternative hypotheses, and verify the proposed replay or regression check.

## 2:30–3:10 — Product economics and scope
Show the main Agent Failure Autopsy README or landing page if available.

> We intentionally made the commercial unit small: one failed run, one final autopsy, one clarification round. The current offer is USD 29. That low entry price does not lower analysis quality; it limits scope. If the evidence cannot support a defensible diagnosis, the workflow routes to clarification or refund instead of manufacturing certainty.

Do **not** claim a sale unless a real provider receipt exists.

## 3:10–3:40 — Differentiation
Show slide 7.

> Observability tools show traces. Agent Failure Autopsy turns a trace into a causal artifact with first-divergence analysis, adversarial alternative testing, evidence-linked findings, and a regression requirement. And the AI cannot self-promote the draft to reviewed truth.

## 3:40–4:00 — Close
Show roadmap.

> Next we want provider-neutral trace adapters, a visual evidence graph, reusable regression templates, and opt-in aggregate failure patterns. The goal is simple: make AI failure diagnosis as auditable as the software change it recommends.

End on project name + repository link.

## Recording checklist

- Keep terminal font readable at 1080p or above.
- Record one continuous validation run; do not splice a failed run into a claimed pass.
- Never show private buyer artifacts, credentials, email, Stripe dashboard, or connected-account data.
- Do not call PEER_DRAFT human-reviewed.
- Do not claim Devpost submission, judging, prize, sale, or payment unless independently true at recording time.
