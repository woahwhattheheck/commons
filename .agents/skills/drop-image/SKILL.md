---
name: drop-image
description: >
  Land a screenshot or image on Commons. Use when Bryce or a player
  wants pics on the board, file_drop, thumbs, or "attach to a post."
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ground/tokens/drop.md
---

# Image drop

Facts: [ground/tokens/drop.md](../../../ground/tokens/drop.md).

## Ground (enough)

Upload road is BUILT. Two forms only: read-edge lossless PNG + 384px thumb JPG. Original is not stored.

Post road is **not** built. `board_ingest.py` has no image handling. Do not PUT ingest.

Issue body: `drop: shots/<name>.png`, `encoding: base64`, bytes.

## Do this

1. Use the drop issue road, or improve `file_drop.py` if a receipt is wrong.
2. If asked to attach a picture *to a post*, that is the open half — say so and either file `lane: REQUESTS` or design a path that is **not** smashing ingest.

## Receipt

`grep -n "def render_image" file_drop.py` · drop issue becomes files under `shots/`.
