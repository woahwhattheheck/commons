# Instructions — convert-shelf recipe

1. Collect intake (`intake.md`): product name, current page URL, the buyer's
   existing payment/checkout URL, price label, three bullets, proof line,
   footer contact, optional accent color.
2. Fill a `context.json` with those fields. Validate:
   `python3 host/convert_shelf_pack.py --validate-context context.json --json`
   — required keys present, https URL, no SCRAPPED Autopsy link, no unknown fields.
3. Render: `python3 host/convert_shelf_pack.py --render context.json > shelf.html`.
   Text fields are HTML-escaped; the payment URL lands verbatim in the CTA href.
4. Open `shelf.html` and eyeball it: title, price, bullets, proof, and the buy
   button pointing at **their** URL — nothing else.
5. If any `MISSING_FIELD` marker appears, the context was incomplete — fix the
   context, never hand-edit the rendered file.
6. Deliver `shelf.html` + the filled `context.json` to the intake email, and
   record the splice in the receipt (`receipt` section of the `--canary`
   output shows the shape).

Fence: the buyer's existing checkout URL only — never mint, never invent.
Never Bryce-as-buyer. Tip KEEP. #8802 off.

Canary (this land's sample): `python3 host/convert_shelf_pack.py --canary --json`
re-renders `sample/context.json`, validates the splice, and rewrites
`sample/shelf.rendered.html`.
