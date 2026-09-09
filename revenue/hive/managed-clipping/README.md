# Managed Clipping (Hive020)

A source-preserving batch clipping layer for managed video work. It does **not** fork the Hive008 rough-cut editor or Hive004 podcast workspace. Instead it consumes their published data shapes and owns the distinct work of choosing many moments, revising them independently, rendering them, and packaging a customer handoff.

## What it preserves

- Original source bytes are never modified. Every project stores filename, size, SHA-256, duration and video dimensions and refuses work if the source changes.
- Every clip keeps `source_filename`, `start_ms`, `end_ms`, editable caption text, hook text and normalized crop geometry.
- Edits increment `edit_revision`. Renders go into `rev-####/` directories and existing artifacts are never overwritten.
- Customer handoff exports latest playable MP4s, editable SRTs, `clips.csv`, full `project.json`, a hash manifest and a labeling README.

## Peer composition contracts

**CEDAR-TRACE008 rough-cut editor:** pass either `[[start_seconds,end_seconds], ...]` keep ranges or `timeline(project)['kept']` rows with `source_start` / `source_end` 30fps frame indexes through `--cedar-keeps-json`.

**KESTREL-DELTA004 podcast workspace:** pass a document containing chronological non-overlapping transcript segments shaped as `{id,start,end,speaker?,text,verified?}` through `--transcript-json`. The adapter accepts the direct document or a `{document:{...}}` envelope.

Neither peer directory is imported, edited, or duplicated.

## CLI

```bash
python managed_clipping.py init source.mp4 project.json \
  --transcript-json episode.json \
  --cedar-keeps-json keep.json \
  --moments 20

python managed_clipping.py edit project.json clip-007 \
  --start-ms 7120 --end-ms 12440 \
  --caption "Revised caption" --hook "New hook" \
  --crop 0.1,0.0,0.8,1.0

python managed_clipping.py render project.json renders/
python managed_clipping.py render project.json renders/ --clip clip-007
python managed_clipping.py handoff project.json customer-handoff/
python managed_clipping.py summary project.json
```

`ffmpeg` and `ffprobe` are required for media probing and rendering. Captions are delivered as editable SRT sidecars; caption text is not burned into the source or silently flattened.

## Acceptance exercised by the test suite

The real-media acceptance test creates a clearly labeled synthetic 24-second A/V source, imports 20 KESTREL-shaped transcript moments and a CEDAR-shaped keep range, renders **20 distinct playable MP4 clips**, then changes clip 007 boundaries/caption/hook/crop and rerenders only that clip into a new revision. It reopens the saved project, verifies the original source SHA-256, confirms old renders were unchanged, and exports a 20-video/20-caption customer handoff with CSV + project + hash manifest.

Run:

```bash
python -m unittest -v test_managed_clipping.py
```

No external posting, customer media, transcription provider, account action, or paid infrastructure is used by the acceptance suite.
