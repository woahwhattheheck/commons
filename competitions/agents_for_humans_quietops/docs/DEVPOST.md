# Devpost submission copy — QuietOps

## Inspiration

Professionals lose hours to routine evidence work, but the risky answer is not “let the agent do everything.” Customer contact, pricing, money movement, contracts and ambiguous evidence are exactly where a background agent should stop and ask. QuietOps was built around that boundary.

## What it does

QuietOps is a background professional agent built with Strands Agents SDK. An Evidence Auditor checks source generations, a Planner chooses bounded work, and a deterministic authority gate decides whether the task can be completed autonomously. Reversible work receives a content-addressed receipt. Real decisions produce a compact decision card and no external action.

The demo reconciles retained financial evidence automatically, while a seemingly simple “send this customer a $3,500 offer” task is blocked for human approval because it combines customer contact, price commitment and an external effect.

## How we built it

Python + Strands Agents SDK (`Agent`, agents-as-tools, `@tool`) with a provider-independent deterministic authority/verifier core. Every Strands tool is bound to a detached invocation snapshot, so the model cannot rewrite the work item before asking the gate. Evidence and receipts are SHA-256 bound, and receipt mint/verify paths independently recompute authority from raw input. Strict JSON, integer minor-unit money, generation alias checks, confidence/ambiguity gates and hostile tests keep model output from becoming authority by prose alone.

## Challenges

The hard part was designing for quiet autonomy without pretending the model can certify its own safety. We split planning from authority and make the execution tool re-check the deterministic gate immediately before work.

## Accomplishments

- Multi-agent Strands composition with explicit tools.
- Deterministic human-vs-autonomous authority boundary.
- Content-addressed execution receipts and offline verifier.
- Credential-free demo plus 55 hostile/invariant tests plus a deterministic authority benchmark in normal and optimized Python.
- AgentCore-ready architecture without making cloud deployment a prerequisite.

## What we learned

A useful background agent is not the one that escalates nothing. It is the one that removes low-value interruptions while making the remaining high-value decisions sharper, rarer and better evidenced.

## What's next

Add provider connectors downstream of the gate, retained provider-generation authority, AgentCore deployment/memory, and vertical adapters for bookkeeping, field-service closeout, procurement and compliance operations.
