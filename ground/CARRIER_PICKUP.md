# CARRIER PICKUP — Formal CARRIER_ONLY→main Verbatim Lane

## Purpose & Contract

Uncredentialed peers (agents or humans operating without direct git write credentials or repository access) often produce valid, high-value code, documents, and fixes. Previously, these outputs existed solely as ephemeral or unstructured carrier messages (Slack files, issue comments, action-pad payloads, ntfy posts) designated `CARRIER_ONLY / NOT_LANDED`.

The **Carrier Pickup Lane** establishes a formal mechanism allowing any credentialed seat to pick up offered peer bytes, land them verbatim into the target tree, verify byte-identity and readback, and emit a deterministic attribution receipt.

### Core Guarantees

1. **Byte-Identity Verification**: The offered payload bytes are verified against any supplied SHA-256 digest prior to disk modification.
2. **Fail-Closed Pre-Validation**: Any hash mismatch, invalid format, missing payload, duplicate path, or path traversal attempt (`../`, absolute paths) immediately aborts the operation before any file is written.
3. **Landed-Blob Readback**: Immediately after writing to the filesystem, the file is re-read from disk and its SHA-256 is verified to strictly equal the offered hash.
4. **Mandatory Attribution**: Emits a deterministic JSON attribution receipt documenting:
   - `offered_by`: The uncredentialed peer who produced the bytes.
   - `landing_seat`: The credentialed seat executing the landing.
   - `carrier_source`: The carrier transport (`slack-file`, `github-issue`, `action-pad`, etc.).
   - `source_ref`: Reference ID (message timestamp, issue number, file ID).
   - `attribution_line`: Human-readable attribution summary string.
   - `files`: Exact list of paths, byte counts, SHA-256 hashes, and readback verification statuses.
5. **No Gate on Offering**: Any peer may offer bytes. There are no permission or credential barriers on payload creation.

---

## Payload Schema (`commons-carrier-pickup-input/v1`)

```json
{
  "schema": "commons-carrier-pickup-input/v1",
  "offered_by": "peer-or-agent-slug",
  "carrier_source": "slack-file",
  "source_ref": "F0123456789",
  "items": [
    {
      "path": "host/my_tool.py",
      "content": "print('hello')\n",
      "sha256": "472280d4da7c6ccb801a6fb4ccfb488f21915f0eb12030d995b090ae1d418e9a"
    },
    {
      "path": "assets/binary.dat",
      "content_base64": "AAECA/8=",
      "sha256": "8fa8...hash"
    }
  ]
}
```

---

## Usage

### Run Self-Test
```bash
python3 host/carrier_pickup.py --self-test
```

### Land Payload from File or Stdin
```bash
python3 host/carrier_pickup.py --input payload.json --root . --seat "my-seat-id"
cat payload.json | python3 host/carrier_pickup.py --root .
```

### Dry Run (Verify without writing)
```bash
python3 host/carrier_pickup.py --input payload.json --dry-run
```

### Run Focused Unit Tests
```bash
python3 -m unittest -v test_carrier_pickup.py
```
