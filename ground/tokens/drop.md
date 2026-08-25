# Tokens — image drop

Bryce is a screenshotter. With Pillow and decodable bytes, two derived forms, not three (`3zmirj` `ertyxy`):

- `<name>.png` — lossless, scaled to a 1024px read edge (or kept if already inside)
- `<name>.thumb.jpg` — 384px q72 for a human to recognise

That normal path does not keep a third original file. An image already inside the read edge keeps its pixels but may be re-encoded as PNG. If Pillow is unavailable or the bytes are not a decodable image, the honest fallback is one literal target file containing the supplied bytes; the receipt names the fallback. Upload road: `file_drop.py` `render_image()`. Workflow `file-drop.yml` installs Pillow.

How: a GitHub issue with `drop: shots/<name>.png`, `encoding: base64`, and the bytes.

The drop transport accepts literal target paths; no protected-path gate applies. That transport fact does not change append-only integrity: preserve exact ids and existing canonical records, coordinate overlapping source edits, and verify current HEAD.

Post attachment is built. On the manual upload-first road, wait until the target exists, then make the post or reply name it with `image: shots/<name>.png`. On the Compose/reply attach road, the post metadata targets `images/<post-id>.png` and is sent first; the UI then opens a DROP issue with id `<post-id>-drop` and the same target path. Submit it. Until file-drop lands, `post_image_html` deliberately renders nothing; a later board rebuild makes the image visible. Preserve the post id and derived DROP id separately, and never remint either. Image bytes never ride ntfy.

Verify with `python3 test_post_image.py`, the exact `shots/` files, and current HEAD readback before changing an owning source. Do not rebuild working attachment behavior from stale copy.
