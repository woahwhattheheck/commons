# Caption transcript intake

Turn supplied SRT or WebVTT captions into an editable, source-preserving transcript handoff. This dependency-free command-line companion adds caption-file intake without creating another podcast workspace, storage service, or browser UI. Python 3.10 or newer is required. No network, model, or provider account is used.

## Run a complete example

From this directory:

```sh
python caption_intake.py examples/demo.vtt \
  --title "Clear project handoffs — fictional interview" \
  --output demo-handoff.zip
python -m zipfile -e demo-handoff.zip demo-handoff
```

Use a new output name for another run; the tool never replaces an existing destination. For a legacy SRT file, provide its known encoding rather than guessing:

```sh
python caption_intake.py captions.srt --encoding cp1252 \
  --speaker "Narrator supplied by the editor" \
  --title "Episode title" --output episode-handoff.zip
```

`--format srt` or `--format vtt` overrides the filename extension. The output parent directory must already exist. Success prints a JSON receipt and exits 0; invalid input or publication failure prints a diagnostic to stderr and exits 2. Neither command changes the input file.

## What the ZIP contains

`source.srt` or `source.vtt` is the byte-for-byte original, including its encoding, byte-order mark, and original line endings. `transcript.json` contains editable transcript segments and source provenance. `manifest.json` records both files' byte counts and SHA-256 hashes. Extract the ZIP, edit a copy of the transcript, and retain the source and original manifest for comparison; editing does not update the original manifest automatically.

A segment has this shape:

```json
{"id":"c00001","start_ms":0,"end_ms":7250,"speaker":"Morgan","text":"How do you keep a small project handoff understandable?"}
```

The document has `schema: "caption-intake/v1"`, `title`, `segments`, and `provenance`. Provenance includes the source hash/size/encoding, original cue identifiers, timing lines, cue settings, raw cue payloads, source line numbers, and retained header/NOTE/STYLE/REGION blocks. Normalized IDs are generated independently of source IDs. `media_verified` is always false: this program does not listen to or transcribe recordings.

The `speaker` field uses one explicit WebVTT voice annotation wrapping the entire cue, or the caller's `--speaker` label. The default `Unspecified` label is not a speaker identification. SRT dialogue prefixes and names in ordinary text are not interpreted as identities. No inference, summary, rewriting, or quote verification occurs.

## Supported input and explicit limits

WebVTT timings support `MM:SS.mmm` and `HH:MM:SS.mmm`; SRT timings require `HH:MM:SS,mmm`. Timings become integers, without a floating-point round trip. Cues remain in source order; equal starts and overlaps are preserved, while backwards starts, nonpositive durations, missing separators, and duplicate nonempty source IDs receive diagnostics. Hours accept two through nine digits. Inputs are limited to 2,000,000 bytes and 10,000 cues.

WebVTT uses UTF-8, optionally with a byte-order mark. SRT defaults to UTF-8 and permits an explicit Python text-codec override. CRLF and CR are normalized only in the editable view, never in the original source copy. The supported syntax is based on the [W3C WebVTT draft, sections 4.1–4.2](https://www.w3.org/TR/2026/CRD-webvtt1-20260520/) and the [Library of Congress SubRip format description](https://www.loc.gov/preservation/digital/formats/fdd/fdd000569.shtml); this converter is not a full rendering engine or conformance validator.

Plain text, character references, balanced bold/italic/underline spans, and WebVTT class spans are supported. Styling is omitted from plain text but preserved in source provenance. A single outer WebVTT voice span may omit its closing tag. Multi-voice cues, partial-voice attribution, ruby, language spans, inline karaoke timestamps, unsupported markup, and SRT positioning extensions require an explicit source edit or another converter; they are not silently discarded. Escape literal less-than signs as `&lt;`. `X-TIMESTAMP-MAP` headers are rejected because applying them requires knowledge of the recording timeline. STYLE/REGION blocks must precede cues. Cue setting strings are retained but not interpreted or comprehensively validated.

## Publication and preservation

The complete deterministic ZIP is built before publication. A private temporary file in the destination directory is flushed and then hard-linked exclusively to the requested path. A retry, existing file, symlink, directory, or concurrent winner cannot be overwritten. Filesystems must support same-filesystem hard links. No fallback replaces the target. This is a local-file operation, not an upload, deployment, or scheduled job. A process crash can leave a private staging file; this is not a claim of power-loss durability or directory fsync.

## Consumer integration

Use `parse_captions(source_bytes, fmt="vtt", title="...")` to consume the normalized document in Python, or extract `transcript.json` from the bundle. Import only `segments` and metadata your receiving application actually supports. Milliseconds must not be passed into a seconds-based field without conversion. The companion does not write to any other application or database.

For the canonical Hive004 podcast runtime, add the recording duration supplied by the editor. Do not infer it from the final caption timestamp. This scripted example explicitly uses a fictional 65-second duration:

```sh
python caption_intake.py examples/demo.vtt --title "Fictional handoff interview" \
  --duration-seconds 65 --synthetic-demo --output demo-episode-handoff.zip
```

The ZIP additionally contains `episode-import.json`: `{title,duration,description,synthetic_demo,segments,chapters:[]}`. Its segment fields are `{id,start,end,speaker,text,verified:false}` in seconds. The original millisecond fields, caption settings and source bytes remain in `transcript.json` and the source copy. Duration must be positive, finite and at most 86,400 seconds. The canonical runtime requires nonoverlapping segments entirely within that duration. The adapter reports overlap or an out-of-range cue without shifting, trimming or discarding anything. Run without `--duration-seconds` for the generic, overlap-preserving bundle instead. Fewer than five cues may be imported but are insufficient for that runtime's draft-generation workflow.

The optional adapter also checks the canonical document limits: title at most 200 characters, speaker at most 120, cue text at most 12,000, and at most 2,000 segments. It reports incompatible inputs instead of truncating, splitting, or guessing. Those limits do not narrow the generic transcript format: omit `--duration-seconds` to preserve a larger generic caption handoff.

The canonical runtime remains owned by its builder under `../podcast-content-workspace/`. The converter does not change or contact it. To import the generated document into a selected local workspace, extract the bundle and run the canonical CLI from this directory:

```sh
python -m zipfile -e demo-episode-handoff.zip demo-episode-handoff
python ../podcast-content-workspace/app.py \
  --db demo-episode-handoff/workspace.sqlite3 \
  --import-document demo-episode-handoff/episode-import.json
python ../podcast-content-workspace/app.py \
  --db demo-episode-handoff/workspace.sqlite3
```

The import command creates a new episode; rerunning it creates another episode rather than updating the first. The server command opens that same local database. Attach the corresponding authorized recording in the workspace before reviewing names/quotes; the fictional caption sample alone is not a verified recording. Retain the original caption handoff beside the content export: the workspace imports the normalized document, not every caption-provenance field.

An existing local HTTP client may POST the unmodified `episode-import.json` bytes to `/api/episodes`. The canonical HTTP body limit is 2 MiB. A valid document can exceed that after JSON escaping; use the CLI import above for those documents rather than dropping text or changing the runtime limit. The integration suite exercises that larger CLI route separately. The converter itself sends no requests.

The adapter is bound to the [published canonical implementation at main `3e3ff8a5`](https://github.com/woahwhattheheck/commons/blob/3e3ff8a5af0b1910b50203e4fe1229134eb9a7ec/revenue/hive/podcast-content-workspace/app.py), Git blob `2051b0fdf43648d857fec34f6a36503adabf9c8f`. Its companion tests execute real converter-to-consumer CLI imports, SQLite reads, a local HTTP import/generate/export workflow, Unicode preservation, schema boundaries, and the large-document CLI route. They import the actual sibling runtime, print its current source hashes, and fail if it is absent; they do not substitute a fake consumer or require that future revisions retain one historical hash. Python callers pass recording duration as a decimal string: `canonical_episode(parsed, "65", synthetic_demo=True)`.

### Managed-clipping follow-through

The same `episode-import.json` is accepted by the sibling `../managed-clipping/managed_clipping.py` runtime through `--transcript-json`. This is a local composition: the caption companion still does not edit, fork, or import the managed-clipping package.

The bundled fictional demo has exactly six eligible caption segments. When demonstrating transcript-driven clipping, request exactly six moments (or fewer):

```sh
python caption_intake.py examples/demo.vtt \
  --title "Fictional clipping handoff" \
  --duration-seconds 63 --synthetic-demo \
  --output clipping-caption-handoff.zip
python -m zipfile -e clipping-caption-handoff.zip clipping-caption-handoff
python ../managed-clipping/managed_clipping.py init \
  /path/to/authorized-source.mp4 clipping-project.json \
  --transcript-json clipping-caption-handoff/episode-import.json \
  --moments 6 --synthetic-demo
python ../managed-clipping/managed_clipping.py render \
  clipping-project.json clipping-renders
python ../managed-clipping/managed_clipping.py handoff \
  clipping-project.json clipping-handoff
```

The source video must be authorized media whose duration and cue boundaries correspond to the supplied captions; the fictional caption sample by itself does not verify any recording. The clipping project records the source byte hash and refuses work if the source later changes.

Do not request more transcript-derived moments than there are eligible segments and then describe the results as distinct transcript moments. The current managed-clipping selector repeats eligible segments when it is asked to fill a larger moment count. The six-cue demo therefore uses `--moments 6`; `test_clipping_consumer.py` asserts the resulting transcript references are exactly `c00001` through `c00006` with no duplicates. If additional non-transcript clips are wanted, choose and document another clipping source rather than presenting repeated transcript references as new transcript-derived moments.

After rendering, the managed-clipping handoff preserves source-linked boundaries and source hash together with playable MP4s, editable SRT captions, `clips.csv`, `project.json`, and its hash manifest. Editing a clip before rendering is revisioned and appears in those editable handoff files without changing the source media.

## Validation

```sh
python -m unittest -v test_caption_intake
python -m py_compile caption_intake.py test_caption_intake.py
# Optional integration suite: requires the real sibling podcast workspace.
python -m unittest -v test_podcast_consumer
# Optional integration suite: requires the real sibling managed-clipping runtime plus ffmpeg/ffprobe.
python -m unittest -v test_clipping_consumer
```

The suite exercises real parsing, Unicode/encoding handling, actual CLI subprocesses, ZIP contents/hashes, existing-target preservation, and competing filesystem publishers. The sample captions are original fictional material, not customer recordings. No claim of audio verification, automatic transcription, browser testing, distribution, or customer fulfillment follows from these tests.

The integrated podcast check ran against canonical source blob `2051b0fdf43648d857fec34f6a36503adabf9c8f`: seven integration tests passed. Python 3.13 emitted SQLite connection `ResourceWarning` messages from that consumer; these are retained in the execution receipt, not hidden or described as warning-free. The managed-clipping composition test uses the live sibling runtime and an original synthetic A/V source; it is distinct from the podcast consumer check. No canonical consumer or managed-clipping runtime changes are included in this companion.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

