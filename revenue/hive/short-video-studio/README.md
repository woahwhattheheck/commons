# Short Video Studio

A local-first short-video production app for `bm-hive-20260908-003`. It turns an editable JSON script/storyboard into a 30–60 second MP4 with audio plus a separately editable SRT caption file that is also muxed into the MP4 as a subtitle track.

## What it does

- three format presets: vertical, square, landscape
- ordered storyboard segments with duration, caption text, color cards, or local PNG/JPEG/WebP assets
- local audio from an owned/licensed file, or a generated demo tone
- exact 30–60 second duration validation
- FFmpeg render with H.264 video, AAC audio, and editable `mov_text` subtitle track
- browser desk for editing JSON, validation, and localhost rendering
- demo source uses only original generated cards/audio; no third-party footage is included
- local path confinement prevents project assets from escaping the project directory

## Run

```bash
python3 studio.py validate demo/project_vertical.json
python3 studio.py render demo/project_vertical.json demo/exports/project_vertical.mp4
python3 app.py --host 127.0.0.1 --port 8877
```

Then open `http://127.0.0.1:8877`. The browser desk does not upload or publish media. Rendered files go under `workspace/exports/`.

## Demo package

```bash
python3 demo/make_demos.py
```

This creates three original 30-second videos in vertical, square, and landscape formats. Each has H.264 video, AAC audio, an MP4 subtitle track, and a sibling SRT source file.

## Tests

```bash
python3 test_studio.py
```

The integration test performs a real 30-second FFmpeg render and verifies video/audio/subtitle streams with `ffprobe`.

## Rights and delivery boundary

Use only customer-owned or appropriately licensed assets. This app performs no network fetches, uploads, account changes, scheduled posts, or platform publication. Tone audio is only a deterministic demo source; production voiceover should be supplied as a local audio file. Platform publishing remains a separate, explicit customer/provider action.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

