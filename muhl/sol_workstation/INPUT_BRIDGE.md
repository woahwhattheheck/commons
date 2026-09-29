# In-place variable input

`input_bridge.py` is the operator's input road for Muhlnickel Titan. It writes the selected published bytes in place, records their previous contents, and surfaces immediate readback. It does not evaluate gates, compute model output, train, or drive a token loop. This is the weightless one-file Titan workbench, separate from Kaggriculture and the Kaggle/ARC agent.

## Bind a real container

For the existing Titan registry:

```powershell
python -B input_bridge.py --file C:/llm/models/titan.gguf --profile titan-registry --registry C:/llm/models/titan_circuits.json --journal C:/path/to/work/native-input-journal.jsonl --port 7882
```

Then open `http://127.0.0.1:7882/`. The page shows the actual bound file and its current size. The registry profile exposes the stored `ram.recv` and `input_addr` byte addresses; it does not invent missing input addresses. A query such as `?window=nring2_000.recv` selects that published field when present. An unknown requested field is reported without silently selecting a different target.

For an existing v4 study specimen:

```powershell
python -B input_bridge.py --file C:/path/to/specimen.mno --profile titan-study-v4 --journal C:/path/to/work/specimen-inputs.jsonl --port 7882
```

The v4 profile reads its in-file registry through `bench.py` and exposes its named input windows. Different file families need their own actual layout contract; an extension or similar filename is not a substitute for one.

## Write and observe

Choose the window, supply hexadecimal bytes, and select the operation:

- **OR** applies a charge mask while preserving already-set bits.
- **Replace** supplies exact variable-data bytes.

The backend opens the selected file with `r+b`, reads only the target input span, journals the before-image and requested bytes, writes only that span, flushes it, and reads it back. It never stages a whole-container browser replacement. A completed receipt describes that I/O; a subsequently different input or output byte is an observation, not something this bridge computes.

The same operations are callable through ordinary HTTP, without a browser:

```text
GET /api/status
GET /api/window?name=start
POST /api/input
Content-Type: application/json

{"operation_id":"my-stable-operation-id","window":"start","mode":"or","hex":"01"}
```

The JSON request is at most 16 KiB and its payload must fit the selected input window. The service binds to loopback and serves its own operator page. It adds no login or per-peer grant. Every caller uses the same published fields and operation receipt rules.

A repeated operation ID with identical input returns the completed receipt; an ID cannot silently acquire different content. Prepared-but-incomplete operations remain recorded for byte readback and reconciliation. The lock coordinates this bridge's requests only; other processes and the file computer may also change storage. An observation must retain that scope.

## Verification performed

The write/replay path was run on an isolated copy of the actual 8,554,889-byte v4 artifact. It changed exactly the published START byte at offset 155650 from `00` to `01`. A streamed full comparison found no other byte changes; the preserved source hash remained unchanged. Repeating the operation returned its receipt and kept the journal at its two prepared/completed records. This verifies the input instrument, not speaking inference or training.

The live Titan registry setup resolved 1,027 input byte windows in the inspected installation. The live bridge was queried read-only; no model write to the original large Titan file was performed during setup.

The legacy desktop input console opens this in-place control for writes. Its local-file display uses bounded slices and understands both the older wrapped registry and the current flat ring registry. A browser `createWritable({keepExistingData:true})` may copy the entire file to temporary storage, so that path is not used by this bridge. [File System Standard](https://fs.spec.whatwg.org/#api-filesystemfilehandle-createwritable).
