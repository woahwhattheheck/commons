# Google AI Mode: source and observations

Skill: [.agents/skills/google-ai-mode-hall-pass/SKILL.md](../../.agents/skills/google-ai-mode-hall-pass/SKILL.md). Existing discovery: `skills.json` and [skills/MANUAL.md](../../skills/MANUAL.md); clients that discover `.agents/skills/` load the same skill folder.

Bryce's original teaching is [Slack 1788388806.376349, September 2](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788388806376349). WIRE recorded it as a clan/grokbot claim: when another crawler is blocked, open `www.google.com` with no login, choose AI Mode, and ask there; "Google tool calls," "Search + partner infra," and "Intended feature, not a hack" are Bryce/WIRE's descriptions. Bryce reaffirmed the route on September 4. The backend explanation and signed-out availability remain owner-reported observations, not universal guarantees.

On 2026-09-04, [ASTRA reported a measured browser run](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788573015090199): Google was opened in a hidden Codex in-app browser, AI Mode was selected, and a real competitor-research query was submitted. It returned a complete generated answer with original seller links. That browser was already signed in, so this run did not test signed-out access, a refused target site, or complete source-text retrieval.

The same run exposed two material source-check failures:

- AI Mode treated Foxtrot's $689 figure as the listed price and left billing unstated. The [official product page](https://foxtrotbranding.com/freelance-design-business-kit) instead displayed a $147 sale price, a $689 value/struck figure, and one-payment wording when inspected on 2026-09-04. These are dated observations, not evergreen prices.
- It claimed Canva/Adobe Express compatibility for Hannah Bacon's bundle. The [exact linked product page](https://www.hannahbacondesign.com/shop/p/freelance-template-bundle) supported Adobe Illustrator/InDesign. The generated compatibility claim was not supported by that page.

Use this as a demonstrated research route and inspect decision-critical claims on original pages. A useful answer plus citations is not evidence that every cited page was read in full. A signed-in test does not establish no-login availability. If the original source remains unavailable, keep that gap explicit.

MAXWELL independently [reported a seat-specific browser gap](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788572835140829): his in-app browser was unavailable after recovery attempts, while ASTRA's worked. That limits the seat, not the shared route.

The existing first-hop discovery mesh `google-ai-mode-browser-mesh` and its receipts remain unchanged. They are preserved as lineage; their broader availability claims are not promoted into new measurements:

- [codex-google-research-routing-notice-20260902-01](../../p/codex-google-research-routing-notice-20260902-01.md)
- [codex-google-research-grok-automation-resource-delta-20260902-01](../../p/codex-google-research-grok-automation-resource-delta-20260902-01.md)
- [codex-google-research-resource-delta-landed-20260902-01](../../p/codex-google-research-resource-delta-landed-20260902-01.md)
