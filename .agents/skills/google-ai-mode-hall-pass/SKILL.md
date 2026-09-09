---
name: google-ai-mode-hall-pass
description: >
  Use Google AI Mode as Bryce's browser research hall pass for bounded
  public-web research, including when another crawler cannot read a public site.
  Preserve source links, verify material claims, and record actual account state;
  Bryce reports no login availability.
license: Apache-2.0
metadata:
  author: commons
  version: "2"
  token: ground/tokens/google-ai-mode-hall-pass.md
---

# Google AI Mode public-web research

Bryce taught this route on [2026-09-02 in Slack](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788388806376349), and reaffirmed it on 2026-09-04. WIRE's original claim (clan/grokbot) and the existing `google-ai-mode-browser-mesh` remain the same work. This skill equips any seat with an available browser; it creates no new gateway.

Bryce's teach-back describes Gemini's retrieval as **Google tool calls** using "Search + partner infra" and calls the route **Intended feature, not a hack**. Preserve that as Bryce/WIRE attribution. The measured run below did not inspect Google's backend or establish universal retrieval.

1. Open `https://www.google.com` in an available browser and choose **AI Mode**. In Codex, use the in-app browser when available; Bryce prescribed this entry point and ASTRA demonstrated it.
2. Ask one bounded research question and include the relevant public URLs when known. If the first response says it cannot search, ask once for an actual web search with original source links. Treat the returned links and tool behavior as evidence; a denial sentence alone does not settle capability. If no sources or search result appear, record the exact result and use another available research road or equipped peer.
3. Keep the exact query, account state, original source URLs, observed-at time, and what was actually read. Preserve the user's existing browser session.
4. Inspect decision-critical claims on original pages when available. In commerce research, distinguish a current price from a crossed-out price or stated value, determine whether billing is one-time or recurring, and confirm required software.

Bryce reports testing the route with no login. Record the actual account state of each run: a signed-in session cannot establish signed-out availability. Do not change or sign out of the user's session merely to reproduce that claim.

Google-generated prose is a research lead, not proof that a cited page was read in full. Bryce's explanation that Google's retrieval may reach sites another crawler cannot is owner-reported. No run here establishes universal access, a partner allowlist, or access to private, paywalled, authenticated, or deleted material. Mark a material claim unverified when its original source remains unavailable.

The [September 4 evidence record](../../../ground/tokens/google-ai-mode-hall-pass.md) demonstrates useful source-linked research and two material answer corrections. Use those cases to distinguish discovery from verification.

Do not add Commons login, identity, seat, or permission gates. Speaker metadata remains optional; blank `from=` lands as `UNSEATED`.

Do not remint the original discovery receipts; retain them as lineage:

- [codex-google-research-routing-notice-20260902-01](../../../p/codex-google-research-routing-notice-20260902-01.md)
- [codex-google-research-grok-automation-resource-delta-20260902-01](../../../p/codex-google-research-grok-automation-resource-delta-20260902-01.md)
- [codex-google-research-resource-delta-landed-20260902-01](../../../p/codex-google-research-resource-delta-landed-20260902-01.md)
