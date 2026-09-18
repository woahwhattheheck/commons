# Checklist — convert-shelf-49 land

- [ ] Intake packet has all 7 required fields (see `intake.md`)
- [ ] `context.json` passes `--validate-context` (0 problems)
- [ ] `PAYMENT_URL` is the buyer's existing https checkout — no minted or
      invented Stripe URL, no SCRAPPED Autopsy link
- [ ] Rendered `shelf.html` contains zero `{{KEY}}` or `MISSING_FIELD` markers
- [ ] The buy button `href` is byte-exact the spliced URL
- [ ] Buyer receives `shelf.html` + their `context.json` (re-renderable)
- [ ] Receipt records cite, splice URL host, render check, USD 0 cash
- [ ] Tip KEEP · #8802 off
