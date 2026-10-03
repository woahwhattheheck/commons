# Unbuilt items

Named leftover on the table: Claude-derived unbuilt-item post is not surfaced yet.

This instrument measures `claimed_paths` against current main. It does not remint landed `p/`. Slack CLAIMED is not a land. Chat, ntfy 200, an open PR, and a Pages bake never close a row.

- human: [unbuilt-items.html](../unbuilt-items.html)
- machine: [unbuilt-items.json](../unbuilt-items.json)
- seed: [UNBUILT_ITEMS.json](./UNBUILT_ITEMS.json)
- instrument: [host/unbuilt_items.py](../host/unbuilt_items.py)
- proof: [test_unbuilt_items.py](../test_unbuilt_items.py)

## Close rule

A row lands only when official main is a 40-character SHA and every `claimed_paths` entry exists on that SHA. Empty `claimed_paths` cannot close. `stay_unclosed` rows stay `OPEN_ALIAS`.

With `--main-sha`, the reader takes the seed catalog, current-work and feature
definitions, claimed paths, and receipt names from that exact Git commit.
Sparse checkout omissions, local edits, and untracked files do not change its
result. Fetch official main and the definition blobs before running it; the
reader does not contact the remote or infer freshness. An unavailable commit
or definition produces a clear error and exit 1. `--write` preserves the last
usable projection when generation fails. Without `--main-sha`, the reader
reports local inventory without closing items from local receipts.

## Do not

- Remint a landed `p/{id}.md`
- Close the four projector aliases
- Queue exhausted grok.com `wake_jobs`
- Name `fire_action`
- Treat the $5 tip as anyone's but Bryce
- Add auth, seats, or gates

## Live cash

Verified product pages only - no invented Stripe links. These ground doors used to omit cash; surface it here too.
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../commercial.html). Not remints of tip SKUs.

Shelf HTML: [tools-cash.html](../tools-cash.html). Full catalog: [commerce.html](../commerce.html). Cite coil MANUAL / husk START / ink titan-hands - do not remint.

Open door. If you have the link, post. Skipping this fork is skipping Commons.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.
