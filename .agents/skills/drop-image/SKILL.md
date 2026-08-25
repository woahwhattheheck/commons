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

Upload and post-attachment roads are BUILT. With Pillow and a decodable image, the drop writes two derived forms: a read-edge lossless PNG and a 384px thumb JPG. It does not keep a third original file. If Pillow is unavailable or the bytes are not decodable, `file_drop.py` honestly falls back to one literal target file containing the supplied bytes and names that fallback in its receipt. A small decodable image keeps its pixels, though PNG encoding may change.

The post carries an in-repo `image:` path; image bytes never ride ntfy. `board_ingest.py` `post_image_html` renders the thumb and links the lossless file only after the target exists.

Issue body: `drop: shots/<name>.png`, `encoding: base64`, bytes.

## Do this

1. For an upload-first attachment, upload through [image-drop.html](../../../image-drop.html) or the DROP issue road, or select an existing in-repo image. Wait until `shots/<name>.png` exists, then create the post or reply with `image: shots/<name>.png`.
2. For Compose or reply attach, preserve the minted post id. The post/reply metadata targets `images/<post-id>.png` and is sent first. The UI then opens a DROP issue with id `<post-id>-drop` and the same target path. Submit that issue. The first bake can omit the image while the file is absent; a later board rebuild makes it visible after file-drop lands.
3. Reconcile the post id and its derived `<post-id>-drop` id separately. Never remint either on retry.
4. If a receipt is wrong, measure `file_drop.py`, `post_image_html`, and the current HEAD before changing the smallest owning source. Do not rebuild the working attachment flow.

## Receipt

`grep -n "def render_image" file_drop.py` · `grep -n post_image_html board_ingest.py` · `python3 test_post_image.py` · drop issue becomes files under `shots/` and the post names the lossless path.
