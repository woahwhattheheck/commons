# titanmcp — Pazhou 2026 Overseas AI Product Competition business plan

**Competition:** Fifth Pazhou Algorithm Competition — Overseas AI Product Competition  
**Track:** AI Product Solution / international group  
**Product:** **titanmcp**  
**Submission status:** **READY AS A PUBLIC BP PACKET; REGISTRATION NOT FILED**  
**Product evidence baseline:** `woahwhattheheck/webmcp-pad main@8c3b31e8a13c6de206a96ec284c92a2476e1f091`  
**Publication boundary:** this preparation packet lives outside the frozen submitted Devpost repository.  
**Public product URL:** https://webmcp-pad.vercel.app/webmcp  
**Public MCP endpoint:** https://webmcp-pad.vercel.app/mcp  

This document is a competition-specific business-plan packet. It does not claim that a competition account has been registered, that an entry has been submitted, that the product has paying customers, or that any prize has been awarded. The already-submitted Devpost/WebMCP repository and live site are under a separate judging freeze; this file must not be used as a reason to mutate those frozen artifacts.

## 1. Executive summary

titanmcp is a general-use context environment where people and software agents coordinate work through the same visible tool surface. It combines shared rooms, role-aware task planning, inspectable agent receipts, an Agent Resources catalog, explicit in-app consent, and one MCP endpoint that can be used both from a browser and by a browserless peer worker.

The product addresses a recurring failure mode in agentic software: capability is fragmented across tools, setup is disconnected from the task that needs it, work ownership becomes opaque, and people struggle to see what an agent changed. titanmcp brings coordination, resource discovery, consent, and action receipts into one context rather than treating each as a separate application.

The current public prototype is deliberately narrow and auditable. It exposes **24 MCP tools**, a **500-row named connector catalog** with source provenance, a live WebMCP page, and a dependency-free Python MCP server. It does **not** currently provide production tenant isolation, durable hosted state, real OAuth connector execution, or real billing. Those gaps define the commercialization roadmap rather than being hidden as finished features.

## 2. Competition fit

The official Overseas AI Product Competition accepts software, hardware, and integrated AI products across ten broad fields, including **AI foundation platforms and toolchains**. The international group explicitly accepts overseas startup teams and individual developers. Initial participation requires a registration form and business plan; full product code or a deployment environment is not required.

Official sources:

- Track: https://www.aicompetition-pz.com/topic_detail/27
- Current participation rules: https://www.aicompetition-pz.com/guidelines

Current published schedule and award structure on the track page:

- Registration: through **September 15, 2026**.
- Preliminary written review: September 16–30.
- Online semifinal: October 14–15, grouped by time zone.
- In-person final: Guangzhou, mid-November.
- First / second / third prizes: **RMB 80,000 / 50,000 / 20,000 pre-tax**.
- Two merit prizes: **RMB 10,000 pre-tax each**.

The published scoring model is:

- 35 points — technical/product leadership;
- 35 points — business model and implementation;
- 20 points — team competitiveness;
- 10 points — project execution feasibility.

This BP is organized to answer those four score families directly.

## 3. Problem

Agent systems increasingly span browsers, APIs, developer tools, research systems, messaging, and business applications. Four practical problems appear repeatedly:

1. **Coordination is outside the action loop.** Humans discuss a task in one place while agents operate elsewhere, producing fragmented status and unclear ownership.
2. **Capability setup is disconnected from need.** An agent discovers that it lacks a resource, but the person must leave the task context and manually reconstruct what to connect and why.
3. **Agent actions are hard to inspect.** A successful tool call may change state without leaving a compact, user-visible receipt tied to the affected object.
4. **Multi-agent work has weak operating structure.** Roles, pieces of work, handoffs, and blockers are frequently represented only as prose rather than shared state.

titanmcp treats these as one context problem: the room where work is coordinated is also where tools, resource requests, role assignments, and receipts are surfaced.

## 4. Product

### 4.1 Shared context

The current tool surface includes room creation, messages, roles, tasks, plans, assignments, and assignment inspection. Humans and agents see the same room transcript and coordination state.

Core coordination tools include:

- `create_room`, `list_rooms`, `post_message`, `list_messages`;
- `invite_agent`, `set_role`, `list_roles`;
- `submit_task`, `plan_task`, `assign_piece`, `list_assignments`.

`invite_agent` is roster metadata only; it does not grant shell or remote-code execution.

### 4.2 Role-aware operators

The product serves operator definitions through `list_operators` and `get_operator`, allowing a room to bind a coordinator, builder, prober, setup operator, or general operator without relying on hidden harness prompts.

### 4.3 Agent Resources

The public prototype exposes a 500-row named connector/resource catalog:

- 27 curated titanmcp connector rows;
- 473 Activepieces community pieces pinned to a specific upstream commit;
- source path and license provenance retained per row.

A missing capability can be expressed in context through `request_setup`. The room receives a need event and a SETUP path. The current prototype records explicit on-page consent and metadata-only wiring rather than performing OAuth.

### 4.4 Inspectable receipts

WebMCP tool execution returns a bounded receipt envelope including a receipt identifier, state version, next actions, and an evidence target that the page can focus. This is designed to make agent action visible rather than silent.

### 4.5 One browser and headless surface

The browser page registers tools through WebMCP (`document.modelContext`). The same product is also exposed through a standard MCP Streamable HTTP endpoint, and `peer_worker.py` demonstrates a browserless peer joining the same room over JSON-RPC.

### 4.6 Low-friction deployment

The server uses Python standard-library HTTP primitives and has no runtime package dependency requirement. A local demo can be started from a clean Python 3.11+ environment without installing an application framework. The deployed Vercel surface routes the web page and MCP endpoint to the same Python function.

## 5. What is working today

The competition entry should distinguish working prototype evidence from roadmap claims.

**Working public prototype evidence:**

- live page: https://webmcp-pad.vercel.app/webmcp;
- live MCP endpoint: https://webmcp-pad.vercel.app/mcp;
- public Apache-2.0 repository;
- `serverInfo.name = titanmcp`, product version `1.4.5` at the pinned baseline;
- 24 tools exposed by the MCP surface;
- 500 named connector/resource catalog rows with deterministic provenance generation;
- shared rooms, messages, roles, task planning, assignments, setup-state stubs, resource catalog, and in-memory billing stubs;
- browser WebMCP and browserless MCP peer paths;
- automated Python and JavaScript contract tests.

**Not claimed as working production capability:**

- durable multi-tenant hosted state;
- user authentication or tenant isolation;
- real OAuth connector execution;
- production secrets storage;
- production billing or collected payment;
- enterprise compliance certification;
- paying customers or recurring revenue.

The public demo is intentionally unauthenticated and in-memory. It must not be presented as a production environment for private customer data.

## 6. Technical differentiation — 35-point scoring family

### 6.1 Context-native capability setup

Instead of asking a user to configure tools before work starts, an agent can discover the missing capability during a task and emit a structured setup need inside the shared room. That setup request is part of the work record rather than an external support ticket.

### 6.2 Human and agent parity

Human page actions and agent tool calls operate on the same MCP-backed state. The product does not create a separate “AI version” of the application with different objects and permissions.

### 6.3 Observable action contract

Receipts, state versions, evidence targets, and visible focus behavior create a concrete audit primitive for agent actions. The commercialization roadmap extends this into durable per-tenant audit history and policy controls.

### 6.4 Standards-based interoperability

The product is built around MCP plus the browser WebMCP surface, reducing dependence on one proprietary agent runtime. A headless peer can use the same protocol without requiring the browser page.

### 6.5 Resource provenance

Connector discovery is not an unsourced list. Community resources are generated from a pinned source tree and carry provenance/license metadata. The current demo does not execute third-party connector code.

## 7. Customer and use cases

### Beachhead customer

The initial commercial customer is a **small AI/software team running multiple agentic workflows across engineering and operations**. Typical buyers include:

- AI application startups coordinating coding, research, and operational agents;
- software agencies delivering repeatable multi-tool workflows for clients;
- internal automation/platform teams that need visible setup and audit boundaries;
- developer-tool vendors that want an MCP-native shared workspace rather than another chat-only interface.

### High-value use cases

1. **Engineering incident / feature room** — planner creates work pieces, builders claim assignments, status and tool receipts remain in one room.
2. **Research-to-build workflow** — agent requests a missing source or connector in context; person grants the exact resource; agent continues without losing the task record.
3. **Client delivery room** — role separation and action receipts make it easier to show what was requested, what was attempted, and what changed.
4. **Internal automation governance** — organization can later attach policy, approvals, budgets, and identity to the same MCP action layer rather than bolting governance on after deployment.

## 8. Competitive position

The product does not attempt to beat every chat application, workflow builder, or connector marketplace on its own category. Its wedge is the combination of:

- shared human/agent context;
- structured work decomposition and role state;
- capability request → consent → continuation inside the task;
- one MCP surface for browser and headless peers;
- observable action receipts;
- open-source, inspectable implementation.

Workflow automation tools are strong at deterministic integrations. Agent chat products are strong at conversation. Developer agent frameworks are strong at programmatic orchestration. titanmcp is positioned between them: the context and control plane in which people and agents coordinate, discover resources, and inspect actions while using external execution systems underneath.

## 9. Business model — 35-point scoring family

The current public prototype has **no live billing and no revenue claim**. The following is the proposed commercial model for post-prototype development.

### Open-source Community

**Price:** free.  
Self-hosted core coordination/MCP surface, public connector metadata, local development, community extensions.

Purpose: adoption, trust, developer contribution, and a low-friction path to evaluate the protocol surface.

### Hosted Team — proposed

**Target launch price:** **US$39 per active user/month**, with a limited free trial.

Adds:

- durable room/task history;
- authentication and isolated workspaces;
- hosted connector credentials and policy-scoped execution;
- shared audit history;
- operational retention and backups;
- basic usage controls.

This is a proposed price, not an existing paid plan.

### Enterprise — proposed

**Target starting contract:** **US$18,000/year**, scoped by seats, retention, support, connector requirements, and deployment model.

Adds:

- SSO / enterprise identity integration;
- advanced policy and approval controls;
- longer audit retention;
- private connector packages;
- deployment/network options;
- support SLA and implementation assistance.

This is a proposed starting point, not a signed or quoted customer contract.

### Usage-based actions — proposed

Execution-heavy connectors can add metered action pricing on top of the workspace subscription. Provider/API charges should remain transparently separated from titanmcp service charges. The current `check_subscription` / `create_play_token` implementation is an **in-memory demonstration only** and does not charge a card.

## 10. Go-to-market

### Phase 1 — developer wedge

- keep the open-source MCP surface runnable with no framework install;
- publish reproducible demos and integration examples;
- target teams already experimenting with multiple coding/research/operations agents;
- convert product-demo users into hosted design partners once durable state/auth is ready.

### Phase 2 — team workflows

Sell the hosted product around concrete multi-agent jobs rather than generic “AI collaboration” language:

- engineering feature/incident coordination;
- research → build → review loops;
- support/operations escalation rooms;
- repeatable agency/client delivery workflows.

### Phase 3 — enterprise control plane

Land larger contracts through governance needs that become unavoidable after pilots:

- identity and SSO;
- retention and audit;
- connector allowlists;
- approval/policy gates;
- budget/action controls;
- private integrations.

### First commercial milestone

The first commercial milestone is not “many connectors.” It is **three external design-partner teams completing repeated real workflows with durable state, authenticated connectors, and observable receipts**, followed by conversion of at least one team to a paid hosted plan. Until that happens, revenue remains unproven.

## 11. Execution plan — 10-point scoring family

### 0–90 days

1. Replace serverless in-memory product state with durable tenant-scoped storage.
2. Add authentication, workspace membership, and tenant isolation.
3. Implement a small set of real, high-demand connectors end to end rather than pretending all 500 metadata rows execute.
4. Add encrypted credential storage and explicit per-connector authorization scopes.
5. Preserve visible receipt/state-version semantics for every mutating action.
6. Replace billing stubs with a real hosted-plan entitlement path only after identity and tenant boundaries are complete.
7. Recruit three external design partners and measure repeated workflow completion.

### 3–6 months

1. Connector execution policy, rate limits, retries, and idempotency.
2. Approval rules for high-impact actions.
3. Searchable durable audit history.
4. Team analytics: work completion, blocker time, connector failure rate, and agent/human handoff latency.
5. Private connector SDK/package path.

### 6–12 months

1. Enterprise SSO and policy administration.
2. Regional deployment/data-retention options where customer demand justifies them.
3. Organization templates for repeatable rooms, roles, and workflows.
4. Marketplace/distribution path for third-party MCP resources and operators.

## 12. Product metrics

The prototype should be evaluated using metrics that reflect completion and trust rather than raw message volume.

**Activation**

- room created;
- first agent task decomposed;
- first resource request resolved;
- first visible receipt inspected.

**Workflow value**

- percentage of tasks reaching completed state;
- median time from missing capability to authorized resource availability;
- human handoffs per completed task;
- percentage of mutating actions with inspectable receipts;
- repeated workflows per workspace/week.

**Reliability**

- connector/tool call success rate;
- state-version conflicts;
- duplicate/ambiguous mutation rate;
- recovery rate after provider/tool failure.

**Commercial**

- design partner → paid conversion;
- paid workspace retention;
- expansion in active seats/workflows;
- gross margin after provider/API pass-through costs.

No current values are claimed for these commercial metrics.

## 13. Team — 20-point scoring family

The official international track permits an overseas individual developer or team. This public BP intentionally does **not** invent degrees, employers, company registrations, revenue history, customer logos, or other credentials.

For the registration form, the entrant should use only verified legal identity, education, organization, and contact information. Those personal fields do not belong in this public repository packet.

The product evidence available to judges is the public working implementation itself: source, live demo, protocol endpoint, tests, provenance tooling, and explicit documentation of limitations.

## 14. Risks and mitigations

### Tenant isolation and privacy

**Current risk:** demo state is in memory and not tenant-isolated.  
**Mitigation:** durable tenant model, authentication, workspace authorization, encrypted credential storage, and explicit retention boundaries before production customer data.

### Connector breadth versus execution depth

**Current risk:** 500 rows are discoverable resources, not 500 production-authenticated live integrations.  
**Mitigation:** commercialize a small real connector set first; keep catalog metadata and executable integration status visibly distinct.

### Agent authority

**Risk:** adding execution increases the blast radius of an incorrect agent action.  
**Mitigation:** closed schemas, scoped credentials, idempotency, approval policy for high-impact actions, state versions, and visible receipts.

### Serverless consistency

**Current risk:** the prototype's in-memory state can be lost or split across instances.  
**Mitigation:** durable shared state is the first commercialization milestone, not a later optimization.

### Standards evolution

**Risk:** MCP/WebMCP interfaces continue to evolve.  
**Mitigation:** isolate protocol adapters, retain contract tests, and keep product semantics (rooms, roles, resources, receipts) independent of one transport revision.

## 15. Intellectual-property and competition boundary

Repository source is already public under Apache License 2.0. The current Pazhou rules separately state that submitted-work ownership is shared by the entrant and organizing committee and that the committee may publicly display entries while promising not to conduct a profit-making transaction with them.

Accordingly, this competition packet is intentionally limited to **already-public product facts and a public business plan**. It must not be expanded with private Commons/swarm materials, credentials, unpublished customer information, private bids, private research artifacts, or any other non-public source merely to improve a competition score.

The registration/submission operator should review the final material actually uploaded under the current rules before accepting the portal terms. This file is a public preparation artifact; it is not proof that those terms were accepted.

## 16. Initial application copy

### Product name

titanmcp

### One-line description

A shared MCP context and control plane where people and agents coordinate work, request resources with explicit consent, and inspect action receipts through the same browser and headless tool surface.

### Product positioning

AI foundation platform and toolchain / agent coordination infrastructure.

### Short product summary

titanmcp gives people and software agents a shared operational context for rooms, roles, tasks, assignments, resources, and inspectable tool receipts. The current Apache-2.0 prototype exposes 24 MCP tools and a 500-row provenance-pinned resource catalog through both a WebMCP page and a standard MCP endpoint. The commercialization roadmap adds durable multi-tenant state, authenticated connector execution, governance, and hosted team/enterprise plans without hiding the prototype's current limits.

### Problem solved

Agentic work becomes difficult to operate when coordination, capability setup, external tools, and action evidence are scattered across separate systems. titanmcp keeps the need, authorization, work assignment, action, and receipt in one context.

### Current stage

Working public prototype / pre-revenue. Live demo and source are public; production multi-tenant identity, durable state, authenticated connector execution, and real billing remain roadmap work.

### Business model

Open-source community core; proposed hosted Team subscription at US$39 per active user/month; proposed Enterprise starting around US$18,000/year based on deployment/support needs; optional transparent usage-based execution charges for action-heavy connectors. These are proposed launch prices, not current revenue.

### 12-month objective

Convert a standards-based public prototype into a durable, tenant-isolated hosted context/control plane, prove repeated real workflows with three external design partners, convert at least one to a paid hosted plan, and build the enterprise identity/audit/policy layer required for larger deployments.

## 17. Registration and submission readiness

The official public registration UI currently requests identity/contact fields including name, country, telephone/SMS verification, email verification, education level, organization/institution, and password. The general rules also require real-name verification.

This repository packet intentionally does not contain those personal values.

Before a portal submission can be truthfully marked filed:

- [ ] Register/login through the official competition portal.
- [ ] Complete required real-name/contact verification with accurate entrant data.
- [ ] Confirm the portal accepts the entrant's overseas telephone/contact route.
- [ ] Select the Overseas AI Product Competition / international group correctly.
- [ ] Confirm final team composition before the team-change cutoff.
- [ ] Upload the final BP derived from this public packet.
- [ ] Re-read the live rules and uploaded files immediately before accepting/submitting.
- [ ] Save the portal submission/readback receipt and exact submitted artifact hash.
- [ ] Do not mark `SUBMITTED`, `ACCEPTED`, `FINALIST`, or `AWARDED` without the corresponding organizer/portal evidence.

## 18. Evidence map

| Claim | Public evidence |
| --- | --- |
| Product identity / tool inventory / architecture | `woahwhattheheck/webmcp-pad` README at the pinned evidence baseline |
| Competition-ready product description | `woahwhattheheck/webmcp-pad/docs/DEVPOST_COPY.md` at the pinned evidence baseline |
| Apache-2.0 license | `woahwhattheheck/webmcp-pad/LICENSE` |
| Live browser product | https://webmcp-pad.vercel.app/webmcp |
| MCP endpoint | https://webmcp-pad.vercel.app/mcp |
| Pazhou track, schedule, prizes, scoring | https://www.aicompetition-pz.com/topic_detail/27 |
| Current competition participation/IP rules | https://www.aicompetition-pz.com/guidelines |

## 19. Final truth boundary

The strongest competition story is not that titanmcp is already an enterprise business. It is that a concrete, public, standards-based prototype already demonstrates the core interaction model and makes its missing production layers explicit. The entry should compete on that inspectable evidence, a narrow commercialization wedge, and a credible path from demo to durable team product—without inventing adoption, credentials, revenue, security certification, or connector execution that does not exist yet.
