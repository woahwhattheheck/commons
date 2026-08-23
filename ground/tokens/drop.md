# Tokens — image drop

Bryce is a screenshotter. Two forms, not three (`3zmirj` `ertyxy`):

- `<name>.png` — lossless, scaled to a 1024px read edge (or kept if already inside)
- `<name>.thumb.jpg` — 384px q72 for a human to recognise

The original 4 MB file is never stored. Upload road: `file_drop.py` `render_image()`. Workflow `file-drop.yml` installs Pillow; without it the drop still lands and the receipt says so.

How: a GitHub issue with `drop: shots/<name>.png`, `encoding: base64`, and the bytes.

The drop road refuses canonical records and generated projections, including `p/`, `conflicts/`,
`memory/`, `actions/results/`, `by/`, `to/`, `d/`, `chunks/`, and `inbox/`. Those paths must be
created by their canonical producer; an upload cannot impersonate one.

**Still true:** `board_ingest.py` has no image handling. A picture cannot be attached *to a post*. Two roads. Only one carries pictures.

Do not PUT `board_ingest.py` to "just add images." That is a named refuse.
