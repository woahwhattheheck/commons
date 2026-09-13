# Agent Failure Autopsy · 10-slide deck

## Slide 1 — Agent Failure Autopsy
**Evidence-linked diagnosis for one failed coding-agent run.**

Coding agents fail across reasoning, tools, files, tests, auth, network boundaries, and orchestration. We turn one failed run into a reviewable causal artifact instead of another confident guess.

## Slide 2 — The problem
The final error is often downstream of the real failure.

- A denied tool may only surface as a missing artifact later.
- A stale file read can masquerade as a test bug.
- A timeout can hide an earlier bad branch.
- An LLM can narrate causality that the evidence never established.

Teams waste time rerunning agents without knowing what actually diverged.

## Slide 3 — The product
One bounded failed run becomes:

1. run reconstruction;
2. first meaningful divergence;
3. primary + contributing causes with confidence;
4. evidence links;
5. adversarial challenge of alternative causes;
6. fix steps; and
7. replay/regression-prevention check.

Commercial unit: one run, one final autopsy, one clarification round.

## Slide 4 — AI with a promotion gate
AI is used for synthesis, but generation is not authority.

```text
bounded evidence -> AI candidate -> deterministic contract checks -> PEER_DRAFT
                                                          |
                                                          v
                                                independent review
                                                          |
                                                          v
                                                  buyer-ready report
```

The model cannot promote its own answer to reviewed truth.

## Slide 5 — Evidence contract
The public fulfillment package enforces bounded intake and reviewable output.

- max 10 files;
- max 25 MB raw evidence;
- max 2,000,000 extracted Unicode characters;
- instructions inside evidence are untrusted data;
- actual buyer artifacts remain private;
- unsupported cases route to clarification/refund instead of forced certainty.

## Slide 6 — Working prototype
The hackathon demo is not a mock screenshot.

`demo_server.py --check` executes the existing public synthetic intake/report through the actual fulfillment validator. The loopback UI displays:

- synthetic intake;
- synthetic autopsy;
- validator receipt; and
- explicit truth/authority boundary.

Python standard library only for the demo surface.

## Slide 7 — Why it is different
**Observability shows what happened. Autopsy argues what caused it—and makes the argument inspectable.**

Differentiators:

- first-divergence framing;
- calibrated causal claims;
- explicit alternative-hypothesis challenge;
- evidence-linked findings;
- replay/regression requirement;
- separate reviewer promotion gate.

## Slide 8 — Real-world value
Who needs it:

- developers running Codex / Claude Code / coding-agent harnesses;
- teams with expensive failed autonomous runs;
- agent-platform builders debugging tool and permission boundaries;
- operators deciding whether a failure is prompt, model, harness, tool, data, or environment.

The underlying offer already has an existing USD 29 checkout. A checkout is not represented as a sale until payment is independently observed.

## Slide 9 — Build integrity
This entry was built during the AI Builders window around an existing product package created during that same window.

The competition wrapper does **not** mutate or remint:

- fulfillment logic;
- report/intake schemas;
- commercial offer terms;
- Stripe IDs or checkout.

It adds a judgeable demo, tests, submission copy, deck, demo script, and readiness record.

## Slide 10 — Roadmap
Next:

- provider-neutral sanitized trace adapters;
- visual evidence graph;
- reusable regression templates for recurrent agent failures;
- privacy-safe aggregate failure taxonomy with explicit opt-in;
- conversion measurement from bounded autopsy to larger implementation work.

**North star:** make AI failure diagnosis as auditable as the software change it recommends.
