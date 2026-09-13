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

## Resumable multi-video production

`production_queue.py` layers a durable campaign queue over the existing renderer without changing `studio.py`. A production manifest binds each job to an exact project revision and a unique MP4/SRT target. Successful jobs are skipped on retry only when the job spec, project bytes, MP4 bytes, and SRT bytes all still match their recorded SHA-256 values; changed or missing artifacts are rendered again.

Start with the three-format example:

```bash
python3 production_queue.py validate production.example.json
python3 production_queue.py run production.example.json --state production-state.json
python3 production_queue.py delivery production.example.json \
  --state production-state.json \
  --output delivery-manifest.json
```

The state file is written atomically after each attempted job, so a later retry can preserve verified successful renders after a partial failure. Project mutation during rendering fails closed. Duplicate job IDs or output targets, path traversal, symlink targets, and source/output aliases are rejected.

A delivery manifest reaches `DELIVERY_READY` only when every listed MP4 and SRT still matches the exact bound project revision and recorded digests. It also carries the campaign's `brand_id`/`preset_id` planning metadata and the renderer project's actual format preset. `DELIVERY_READY` is local artifact integrity only: the manifest explicitly records that no customer delivery, external publication, provider action, payment verification, or revenue recognition occurred.

## Tests

```bash
python3 test_studio.py
python3 -m unittest -v test_production_queue.py
python3 -O -m unittest -v test_production_queue.py
```

The original integration test performs a real 30-second FFmpeg render and verifies video/audio/subtitle streams with `ffprobe`. The production-queue suite exercises resume, stale revisions, tampered outputs, partial failures, deterministic delivery, path and alias guards, and mutation-during-render fail-closed behavior.

## Rights and delivery boundary

Use only customer-owned or appropriately licensed assets. This app performs no network fetches, uploads, account changes, scheduled posts, or platform publication. Tone audio is only a deterministic demo source; production voiceover should be supplied as a local audio file. Platform publishing remains a separate, explicit customer/provider action.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
