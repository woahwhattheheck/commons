# Managed clipping service — Hive020

This directory is the bounded production workspace for `bm-hive-20260908-020`.
It turns one source recording into an editable, rerunnable 20-clip handoff while
preserving source synchronization. It does **not** replace the peer-owned
rough-cut editor or podcast workspace.

## What it owns

- source filename, hash, and millisecond boundaries per clip;
- editable caption text, crop/framing, hook variant, and revision number;
- FFmpeg rendering of one clip or the full selected set;
- sidecar SRT captions;
- editable JSON project + CSV handoff;
- a ZIP containing the 20 playable exports and captions.

`normalize_external_moments()` is the compatibility seam for peer timeline or
transcript exports. It accepts `clips`, `moments`, or `segments` arrays with
`start_ms`/`end_ms` (or `start_millis`/`end_millis`) and caption/text/transcript.
When a peer publishes a stronger interface, this adapter can consume that shape
without importing or rewriting their app.

## Runnable self-authored demo

The demo is labeled **SELF-AUTHORED SYNTHETIC DEMONSTRATION**. It is test-pattern
media generated locally with FFmpeg; it is not customer media or customer
fulfillment.

```bash
python3 managed_clipping.py demo demo-workspace
```

That command creates a 30-second synthetic source, 20 distinct source windows,
20 playable MP4s, 20 SRT captions, `project.json`, `clips.csv`, and
`managed-clipping-demo-bundle.zip`.

Edit and rerender exactly one clip:

```bash
python3 managed_clipping.py edit \
  --project demo-workspace/project.json \
  --clip-id clip-07 --start-ms 7800 --end-ms 8750 \
  --caption 'Edited caption for clip seven.'

python3 managed_clipping.py render \
  --project demo-workspace/project.json \
  --output-dir demo-workspace/renders \
  --clip-id clip-07
```

The renderer writes through a temporary file and atomically replaces only that
managed output; unrelated files and other clips are not removed or rewritten.
The source SHA-256 is checked before every render so a project cannot silently
render against changed input media.

## Retained demonstration package

`demo/managed-clipping-demo-bundle.zip` is a complete retained demo: the generated
source, editable project, CSV, 20 playable MP4 exports and 20 SRT caption files.
Clip 07 is revision 2 after the required boundary/caption edit and one-clip rerender.
The adjacent `SHA256SUMS.txt` records each retained playable clip. Extract the ZIP
for the full runnable package; the source is kept inside the ZIP to avoid a second
repository copy.

## External intake

```bash
python3 managed_clipping.py init --source recording.mp4 \
  --moments moments.json --project project.json
python3 managed_clipping.py render --project project.json --output-dir renders
python3 managed_clipping.py handoff --project project.json \
  --output-dir renders --handoff-dir handoff
```

## Acceptance

```bash
python3 test_managed_clipping.py -v
python3 -m py_compile managed_clipping.py test_managed_clipping.py
```

The focused suite generates real media, verifies all 20 exports with `ffprobe`,
changes one clip's boundary and caption, rerenders only that clip, reopens the
saved project, rechecks the source hash, and verifies the final CSV/ZIP handoff.
No external posting, provider mutation, or customer data is involved.
