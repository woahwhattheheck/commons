# Customer-facing link boundary

Bryce's current customer boundary is direct: Commons and GitHub are internal evidence surfaces, not customer destinations. Customer copy should point to a clean standalone branded experience and a direct transaction or procurement path.

`host/customer_link_boundary.py` is a pure-stdlib preflight for customer-facing text. It reports and rejects:

- GitHub, Gist, API, Raw, asset, and other GitHub-hosted URLs;
- GitHub Pages hosts;
- Commons machine links and the Commons Slack workspace;
- plain, bare-host, Markdown, Slack angle/pipe, scheme-relative, mixed-case, trailing-dot, and backslash link forms.

It returns exact offsets, raw text, normalized URL, host, and reason for every finding. Ordinary branded domains and direct Stripe links pass.

```console
python host/customer_link_boundary.py customer-message.txt
```

Exit 0 means the text contains no forbidden customer link; exit 1 carries a JSON violation report. This tool is scoped to customer copy. Internal Commons and Slack evidence remain available and unchanged.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260905-08 — do not remint.
