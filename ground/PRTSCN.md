# PrtScn is the write road

Owner approved 2026-08-20. Additive. Does not replace `file_drop.py`. Pictures still ride the **upload road**, not ntfy.

The viewers already render state literally. A screenshot is a timestamped out-of-band capture. Two shots are a measurement. A number about the machine with no pair of images is talk.

## Pair convention

Same id stem, two files, existing compressor:

```
drop: shots/<stem>-a.png
id:   <claim>-shot-<stem>-a
encoding: base64

---
<bytes>
```

Then the same stem with `-b`. `file_drop.py` stores the model PNG and the thumb. It does not overwrite. Pick a new stem.

## Doors

- `look.html` — drop two local files, see A / B / XOR + box. No verdict.
- `shots.html` — same look, plus the issue-body recipes for the upload road.
- `imgdiff.py` — the original instrument. Untouched. Historical artifact and still the CLI.

Bytes never ride ntfy. Cite `carrier.js` and directive 5.

HTTP is not the computer.
