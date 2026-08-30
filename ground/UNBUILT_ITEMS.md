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

## Do not

- Remint a landed `p/{id}.md`
- Close the four projector aliases
- Queue exhausted grok.com `wake_jobs`
- Name `fire_action`
- Treat the $5 tip as anyone's but Bryce
- Add auth, seats, or gates
