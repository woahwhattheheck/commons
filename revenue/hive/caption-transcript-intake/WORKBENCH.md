# Caption batch intake workbench

A local browser companion to the existing caption converter, not another podcast editor. It parses supplied SRT/WebVTT files, shows source-linked cue previews and actionable errors, and downloads the existing source-preserving handoff ZIPs individually or in a complete batch. It does not transcribe, verify a recording, infer speakers, contact providers, or import into a workspace automatically.

## Start

From this directory with Python 3.10 or newer:

```sh
python workbench.py
```

Open the printed `http://127.0.0.1:8766/` address. Use `--port 8767` to choose another port, or `--port 0` to select an available one. Ctrl+C stops the server. No dependencies, build command, account, or database are required. Keep `workbench.py`, `workbench.html`, `workbench.js`, and the existing `caption_intake.py` together. Open the local address rather than opening the HTML file directly.

Select or drop caption files. Click a filename to change its title, explicit format, known encoding, default speaker label, or optional known recording duration. The file's original bytes remain unchanged. Checkmarks choose the batch; duplicate filenames remain separate entries. Removing an entry or clearing the selection affects only this browser tab.

**Preview selected** reports each file separately. Click a file to inspect the normalized captions alongside their original source IDs, line numbers, timing and markup. Search by text, speaker or cue ID and page through all matching cues. The last caption timestamp is displayed as a caption boundary, never as the recording's duration.

**Download this handoff** returns the existing converter's ZIP. **Download selected batch** returns one outer ZIP containing an individual handoff for each selected entry and a batch manifest. An invalid selected file prevents the whole batch download: fix its options or explicitly deselect it. Valid selected files are never silently substituted for an incomplete batch. Downloads parse the current source/options again; old previews cannot authorize a different export.

## Optional podcast/clipping import

Leave duration empty for the generic handoff, which preserves overlaps. Supply the recording duration in decimal seconds only when it is known. This adds the existing `episode-import.json` to that file's ZIP using `canonical_episode()` and its current consumer constraints. Incompatible overlaps, out-of-range cues and consumer size limits appear as errors while the generic cue preview remains available. Clear duration to retain a generic handoff rather than altering captions to fit a consumer.

The fictional-demonstration checkbox labels the optional episode import; it does not verify audio or alter the original caption file. The retained `examples/demo.vtt` is an explicitly fictional six-cue example. A supplied demonstration duration of 65 seconds fits it; this is not evidence of a recorded interview.

Import the exported document deliberately through the existing podcast or managed-clipping workflow described in [README.md](README.md#consumer-integration). This workbench never writes to their databases or creates repeated episodes behind the scenes.

## Preservation and limits

Each individual ZIP is produced by the unchanged `create_bundle()` API and contains the byte-for-byte original, `transcript.json`, its manifest, and the optional episode import. Batch member names are an ordinal plus a normalized filename stem, so duplicate names cannot overwrite one another. `batch-manifest.json` maps each member to its original filename, source hash, format, encoding, cue count, import mode, and ZIP size/hash. Both archive layers use fixed timestamps and deterministic ordering for identical inputs/options.

The workbench accepts at most 20 files, 2,000,000 original bytes per file, 20,000,000 original bytes and 50,000 cues per request. Each file retains the parser's 10,000-cue maximum. JSON requests are capped at 28,000,000 bytes including base64 expansion. Split larger jobs. The single-request server processes conversions serially rather than multiplying memory use across parallel requests. This is a local operator tool, not a production upload service.

Previews show 100 matching cues per page and at most 4,000 characters of each cue's normalized text and original payload, with visible truncation notices. They list the 100 most frequent speaker labels and report the full distinct-label count. **Exports contain all accepted cues and complete text**, irrespective of preview search, offset or display truncation. Overlap count means cues whose start falls before the latest earlier end; it is not a count of all overlapping pairs.

All source bytes and parsed documents are transient request data; the server does not write uploads, captions, exports, or request logs to disk. The tab retains selected bytes until cleared, reloaded or closed. This is not a claim of secure memory erasure. Browser downloads persist wherever the operator saves them. No third-party scripts, fonts, telemetry or network requests are included. The server binds only to loopback and exposes no arbitrary-file download route.

## Local API

`GET /api/info` reports limits. POST JSON to `/api/preview`, `/api/export` (exactly one file), or `/api/batch` (one or more files):

```json
{
  "files": [{
    "name": "interview.vtt",
    "source_base64": "<base64 of the original bytes, not decoded/re-encoded text>",
    "title": "Interview handoff",
    "format": "vtt",
    "encoding": "utf-8-sig",
    "speaker": "Unspecified",
    "duration_seconds": null,
    "synthetic_demo": false,
    "query": "",
    "offset": 0
  }]
}
```

The preview returns HTTP 200 with `ok` and one indexed result per input, including errors. `parsed:true, ok:false` means generic parsing succeeded but the requested export needs attention. Invalid export entries return HTTP 422 and JSON diagnostics, **not a partial ZIP**. Malformed/oversized requests return HTTP 400; unexpected runtime errors return HTTP 500 and a terminal traceback. Successful exports return `application/zip`. Supply Content-Length and application/json; chunked request bodies are not supported. An unreadable UI asset or failed port bind exits the CLI nonzero with a diagnostic.

This implementation composes the existing caption intake and keeps its supported syntax, provenance semantics, and consumer adapters unchanged. It adds no test suite, CI workflow, retained execution transcript or media fixture.
