# Public Surface Link Guard

Owner policy: a public/customer-facing/storefront artifact must not link back to Commons unless Bryce explicitly approves one exact, bounded exception. Public artifacts stand on their own and use product-specific destinations; internal provenance stays internal.

This package is an **offline fail-closed CI guard**. It performs no network crawling, no sends, and no deployment. The manifest is a closed classification ledger for the in-scope text surfaces: every listed file is explicitly one of the public classes or `INTERNAL`. `INTERNAL` is an explicit classification, not an omission convention.

## Manifest

```json
{
  "schema": "commons.public-surface-link-guard/v1",
  "surfaces": [
    {
      "path": "site/index.html",
      "class": "STOREFRONT",
      "public_base_url": "https://product.example/"
    },
    {
      "path": "internal/provenance.md",
      "class": "INTERNAL"
    }
  ],
  "blocked_destinations": [
    {
      "id": "private-sales-board",
      "kind": "COMMONS_BOARD",
      "destination": "https://ops.example/internal/commons-board/",
      "match": "SUBTREE"
    }
  ],
  "exceptions": [],
  "aliases": []
}
```

Public classes are `STOREFRONT`, `CUSTOMER_FACING`, `PUBLIC_PRODUCT`, `PUBLIC_COMPETITION`, and `PUBLIC_DELIVERABLE`. `INTERNAL` files are opened through the same generation-safe custody boundary but are not subjected to the public-backlink ban.

The guard always blocks the Commons GitHub repository and Commons GitHub Pages subtree. `blocked_destinations` extends the policy to owner-known Commons pads, boards, receipts, action surfaces, or other internal destinations without network lookup. Each rule is `EXACT` or `SUBTREE` and has a typed `COMMONS_*` kind. This is how non-GitHub internal surfaces enter the same policy boundary.

Aliases are retained facts, not redirects fetched at runtime. Their target must already be blocked by a built-in or `blocked_destinations` rule. A link to the alias is then reported against the blocked target.

## Exceptions

An exception requires exact public path + exact normalized destination + expiry date + reason:

```json
{
  "path": "site/legal.html",
  "destination": "https://github.com/woahwhattheheck/commons/tree/main/example",
  "expires_on": "2026-09-30",
  "reason": "Explicit Bryce-approved temporary migration reference"
}
```

There are no wildcard exceptions. Expired exceptions fail closed. The production CLI uses a process-owned UTC date captured in a private closure; ordinary module-global rebinding cannot rewind it. The public `scan_manifest(..., as_of=...)` seam is explicitly labeled `HISTORICAL_EXPLICIT` and is for deterministic tests/audits, not a current CI verdict.

## Detection and custody

The scanner recognizes bare URLs, Markdown links, HTML `href`/`src`/`action`, and autolinks. It handles HTML entities, JSON escaped slashes / common ASCII `\u00xx` URL escapes, up to three percent-decoding layers, protocol-relative links, HTTP(S) browser-style backslashes, default ports, dot segments, and common terminal punctuation. Relative links are resolved only when the manifest supplies `public_base_url`.

Manifest and surface files are opened component-by-component with no-follow semantics. Reads are bound to the opened inode generation and then the full visible component chain is re-opened and compared after read. A parent/leaf remint therefore fails closed instead of scanning old bytes while reporting a new visible pathname.

Every violation includes deterministic remediation text: remove the Commons destination or replace it with a product-specific public URL; an exception must be an exact owner-approved path+destination+expiry record.

## Run

```bash
python -m tools.public_surface_link_guard.cli public-surfaces.json --root .
```

Exit codes:

- `0`: no prohibited public Commons backlink found;
- `1`: prohibited backlink(s) found;
- `2`: invalid manifest/input or unsafe file/generation boundary.

The JSON report includes `evaluation_mode`, exact file/line/link/destination/reason/remediation, active exceptions, explicit INTERNAL/public scan classifications, and hard-false external authority. Integrating this guard into another public/storefront repository **must not add a backlink to Commons**.
