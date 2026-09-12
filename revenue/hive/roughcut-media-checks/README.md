# Rough-cut media checks

A dependency-free Python companion for the canonical Hive 008 editor at
`revenue/hive/roughcut-editor/`. This directory does not introduce a second
editor. It generates an owned audiovisual pulse recording and checks an
editor's actual MP4 render against its original-source keep ranges.

The checker decodes white flashes from video pixels and tone starts from audio
RMS measurements. A correct duration alone cannot make a wrong cut pass. It
also hashes the original source before and after verification, and checks that
the rendered file did not change during measurement.

## Requirements and first run

Use Python 3.10 or later, FFmpeg with libx264/AAC and the signalstats/astats
filters, and ffprobe on PATH. No Python packages, account, network request,
external model, or customer recording are required.

From this directory:

```sh
python -m unittest -v
mkdir -p /tmp/roughcut-pulses
python media_checks.py generate /tmp/roughcut-pulses/source.mp4 --seconds 1200
```

Generation creates `source.mp4` and `source.mp4.fixture.json`. Existing output
files are preserved: use a new filename for another fixture. The default
recording is 160 by 90 pixels at 25 fps with 20 aligned white flashes and 997 Hz
tones. It is explicitly synthetic, not a human recording or editorial sample.

Import that MP4 into the editor, cut source seconds 300 through 310, and export
its normal MP4. Save the retained source ranges, in seconds, as `keep.json`:

```json
[[0, 300], [310, 1200]]
```

Then measure the actual exported file:

```sh
python media_checks.py verify /tmp/roughcut-pulses/source.mp4 edited.mp4 \
  --manifest /tmp/roughcut-pulses/source.mp4.fixture.json \
  --keep keep.json --report edited-report.json
```

Restore the cut in the editor and export a second MP4. Use `[[0, 1200]]` as its
keep plan and run the same command with the restored render. The edited plan
expects 1,190 seconds and 19 retained markers; the restored plan expects 1,200
seconds and all 20 markers. Both operations must leave the original unchanged.

Exit status is 0 for a passing measurement, 1 for a measured mismatch, and 2
for an invalid input or media-tool execution problem. Reports are also written
to stdout. Keep ranges are ordered, nonoverlapping half-open source intervals;
at most 256 are accepted. The report records expected and observed marker
positions, per-channel errors, A/V offsets, durations, and source/render hashes.

## Canonical editor integration

CEDAR-TRACE provided the editor's current integration contract in the
[Hive 008 source thread](https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788867459726719?thread_ts=1788849545.913639&cid=C0C05UU6WKG).
Its `timeline(project)['kept']` rows use 30 fps frame coordinates. Convert those
coordinates to source seconds without rounding them again:

```python
keep = [
    [row['source_start'] / 30, row['source_end'] / 30]
    for row in roughcut.timeline(project)['kept']
]
result = media_checks.verify(source, exported_mp4, fixture_manifest, keep)
```

Import each module from its respective directory. Use the original generated
fixture path as `source`, not the rendered output. This contract is documented
for consumption; the retained validation here used the independent test
renderer, not CEDAR's editor. A consumer run must identify its actual editor
source pin and keep plan before being reported as integrated validation.

## Measurement limits

The default tolerance is 80 milliseconds. Video events use decoded frame
presentation timestamps; audio uses decoded 10-millisecond RMS blocks. A
reported zero offset means zero at those resolutions, not sub-frame or
sample-exact synchronization. Render codec behavior can affect detection.

Cuts in this fixture must avoid an entire pulse plus one source-frame margin.
An intersected pulse is an unsuitable test plan and produces an input error,
not a claimed editor defect. At least one complete pulse must remain. Periodic
markers cannot establish visual content identity or catch every possible edit
between markers. Use this companion alongside ordinary editor behavior tests.

This is not an ASR system, a silence detector for real speech, a natural-speech
coherence assessment, a caption correctness check, or browser/customer
acceptance. No live-browser pass or human-recording fulfillment is asserted.
The original source is never edited by the checker. Fixture video and manifest
are separate creations, not a crash-atomic pair; retain any interrupted output
and generate a fresh pair under a new filename.

## Retained validation

`validation.json` records the actual cloud-container validation on September
8, 2026: 12 unittest methods passed with no skips; the 20-minute reference-render
exercise passed both the cut and restored plans. The short negative cases use
a real 300-millisecond delayed audio render and a wrong cut with the correct
duration and marker count. Both are rejected.

To reproduce the long reference-render exercise without an editor, use
`render_reference` from `test_media_checks.py` for the two keep plans above and
then call `verify`. That helper exists only for these regression tests; the
product consumer should use its own ordinary export path. Generated media are
not stored in Git. Source/codec versions can change encoded hashes, so always
use the manifest produced with your own generated source.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
