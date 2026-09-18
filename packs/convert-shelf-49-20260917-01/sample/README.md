# Sample — convert-shelf-49 canary

`context.json` is a fictional indie SaaS splice ("Queueboard"). Its
`PAYMENT_URL` uses the reserved `checkout.example.com` host — a placeholder,
not a minted or invented Stripe link.

`shelf.rendered.html` is byte-for-byte the output of:

```
python3 host/convert_shelf_pack.py --render packs/convert-shelf-49-20260917-01/sample/context.json
```

Regenerate + verify the whole sample hermetically:

```
python3 host/convert_shelf_pack.py --canary --json
```

The canary re-renders the template, checks that every `{{KEY}}` resolved,
that the rendered `href` carries exactly the spliced URL, and writes the
rendered file back. A real customer land replaces `context.json` values with
the buyer's fields and their **existing** payment link — the pack never
mints one.
