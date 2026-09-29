# Using the Muhlnickel Titan bench

This workbench is for **Muhlnickel's weightless, one-file speaking Titan**, separate from Kaggriculture Titan and the Kaggle/ARC agent. The command-line instruments and standalone visual bench read the actual existing files. They do not run a model or evaluate gate records.

`bench.py` needs only Python's standard library. Run it from this directory or use its absolute path. `PROJECT.json` identifies the project and names existing artifacts. It resolves the current owner's Desktop automatically; the research path is relative to this workstation. `--root desktop=...`, `--root research=...`, and an artifact command's `--file ...` select another existing installation or specimen without copying it.

The [existing live viewer](LIVE_VIEWER.md) complements the saved snapshots with current bounded byte/registry reads. Its documented no-baseline launch avoids a whole-file startup read.

The [in-place input bridge](INPUT_BRIDGE.md) supplies variable data and charge masks to published inputs, with before-images and replay receipts. It is a separate write instrument; `bench.py` itself remains read-only.

## First operations

```powershell
python -B bench.py status
python -B bench.py tools
python -B bench.py tools png
python -B bench.py inspect titan-v4
python -B bench.py bytes titan-v4 target0 --length 8
python -B bench.py records titan-v4 candidate_bridges --count 8 --bits
python -B bench.py trace titan-v4 hit0 --hops 5
python -B bench.py trace titan-v4 candidate --direction downstream --hops 5
python -B bench.py joins titan-v4 --out C:/path/to/new-run/joins.json
python -B bench.py html titan-v4 --out C:/path/to/new-run/bench.html
```

The visual bench is one standalone HTML file. Open it locally, filter by a signal, address, operation, or record table, and click an input/output address to follow its readers and writers. `in:8548720` and `out:8548720` select consumers and producers explicitly. It contains the inspected records and byte windows as a dated snapshot; reload the underlying file by running the command again. The HTML table shows the first 300 matches and reports the full match count, so narrow a query to inspect every matching record.

The `bytes` command shows literal bits and hex values. `records` reads fixed physical rows without evaluation. `trace` follows addresses up or downstream and retains cycles with a finite hop boundary. `joins` reports cross-table connections and every destination with multiple writers; self-editing can deliberately target stored records, so the output is a wiring inventory rather than an automatic defect verdict.

For a destination inside a record table, the row names the affected record, opcode/address field, and byte within that field. The visual address search also includes the record containing that byte. This makes a self-fabrication write inspectable alongside ordinary state-wire connections.

## Observe a native operation

Capture the specimen before and after an operation using its existing input/fire tool. This bench itself does not fire or mutate the source container.

```powershell
python -B bench.py capture titan-v4 --file C:/path/to/specimen.mno --note "before named operation" --out C:/path/to/new-run/before.json
# Perform the intended operation using its existing file-published input route.
python -B bench.py capture titan-v4 --file C:/path/to/specimen.mno --note "after named operation" --out C:/path/to/new-run/after.json
python -B bench.py compare C:/path/to/new-run/before.json C:/path/to/new-run/after.json --host-input target0 --host-input start --host-input ring_forward --host-input ring_reverse
```

Each capture reads named byte windows and hashes every named record table in bounded chunks. It records source size and whether the file's size/mtime changed during reading. A comparison reports exact changed bytes, declared host-input windows, table-hash changes and size change. Input labels are supplied by the operator; they do not prove who wrote a byte. Uncaptured bytes and outputs are explicitly outside that capture's coverage. For two pre-existing specimens, add `--specimens`; matched layout is required and the result does not imply a causal before/after experiment.

Outputs are created with exclusive file creation, so reusing a result path reports an error instead of overwriting a container or earlier result. Pick a new run directory/name for each operation. Source files are always opened read-only.

## Artifact contracts

| Name | Layout read | Current purpose |
| --- | --- | --- |
| `titan-v4` | Actual appended `MUHLAFB1` registry, seven record tables and named byte windows | Candidate/reader/score wiring under development |
| `autofab0` | Whole gate-first stream of 25-byte records | Existing self-fabrication part; addressed space can extend beyond its current EOF |
| `reader1` | External layout sidecar plus record stream | Eight-byte cursor/target comparison part; bare logical offsets are not blindly treated as live container state |
| `visible6` | External sidecar's state, observation and record regions | Headerless ring geometry and its observation windows |

Opcode numbers are decoded only where this profile names its operation map. A numeric-only map stays numeric; do not apply a different container's map by resemblance. Project and capability labels in the registry are recorded context, separate from freshly inspected bytes.

## Building while reading

The original document shelf remains in `README.md`, `TOOL_SHELF.md`, `DOC_MAP.md`, `LATER_IDEAS.md`, and `ROOTS.tsv`. Fleet reading supplies complete source contracts and coverage. Use those contracts to add named artifact profiles or a new instrument command, then run it on the real file and retain the result. A directory name, a search hit, or an opened large file does not count as complete reading.

Use the permitted one-time host prefabrication for accurate layout when needed. Keep speaking inference, deterministic training, correctness grading and recursive feedback in the computer file. The accepted adder measurement remains the starting point for development; this bench adds tools for the next operation.
