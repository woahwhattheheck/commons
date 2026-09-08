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

The canonical runtime remains owned by its builder under `../podcast-content-workspace/`. This package neither changes it nor sends HTTP requests. The adapter implements the builder's [reported import contract](https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788867534373669), with local conversion and CLI tests. Execution against the published Store/HTTP implementation is a separate integration check, not claimed by this initial adapter delivery. The self-contained caption handoff works independently. Python callers pass the recording duration as a decimal string: `canonical_episode(parsed, "65", synthetic_demo=True)`.

## Validation

```sh
python -m unittest -v test_caption_intake
python -m py_compile caption_intake.py test_caption_intake.py
```

The suite exercises real parsing, Unicode/encoding handling, actual CLI subprocesses, ZIP contents/hashes, existing-target preservation, and competing filesystem publishers. The sample captions are original fictional material, not customer recordings. No claim of audio verification, automatic transcription, browser testing, distribution, or customer fulfillment follows from these tests.
