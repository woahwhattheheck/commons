# Existing live viewer on the bench

The owner's existing `MUHLNICKEL_APP/live_viewer` contains a bounded live instrument that complements `bench.py`'s named artifact snapshots. It is for the same Muhlnickel computer project, separate from Kaggriculture Titan and the Kaggle/ARC agent.

## Start without a full-file baseline

From the installed `Desktop/MUHLNICKEL_APP/live_viewer` directory:

```powershell
python -B muhl_live_backend.py --port 7881 --no-baseline --no-sweep
```

This binds only to `127.0.0.1`. Its existing defaults select `C:/llm/models/titan.gguf` and `C:/llm/models/titan_circuits.json`. The two switches skip the initial whole-file baseline read and disable repeating sweeps. Startup opens a read-only mapping, reads the circuit registry, allocates the observation arrays, and starts the existing directory/journal notifier. It does not change the model file or execute its gate records.

Open the existing `live_viewer.html` in a browser. Its default API is `http://127.0.0.1:7881`; the `?api=http://127.0.0.1:7881` query can select it explicitly. The backend serves API responses, not that HTML file. The page's initial requests are status, tiles and the event stream; selection makes bounded byte/region requests.

## Useful exact requests

```text
GET http://127.0.0.1:7881/api/status
GET http://127.0.0.1:7881/api/bytes?off=93711094958&len=65
GET http://127.0.0.1:7881/api/regions?off=93711094656&len=64
```

These two windows refer to the recorded resident foundry in this installation; first use the current registry to resolve the component when working with another file/version. `/api/bytes` uses absolute byte `off` and `len` from 1 through 4096. `/api/regions` returns registry spans intersecting an explicit window. The raw-byte response contains bytes, bit strings and observation history; it is an instrument read, not an inference result.

The live notification stream explicitly reports `change_detection_scope=host_writes_only`. It tails append-only journals and observes journalled writes; a quiet notification stream does not measure autonomous activity outside that journal. With no baseline, unobserved tiles stay unobserved until sampled or journalled.

## Choose the appropriate instrument

Use `live_viewer.html` for bounded current bytes, registry spans and journal-driven observations. Use `bench.py` for named v4/reader/autofab layouts, raw records, wiring traces and saved before/after comparisons.

The neighboring `all_bits.html` has a different workload: its current source allocates a 1 GiB GPU texture, fetches large chunks automatically and writes measurement receipts through its backend. It is not started as part of this bounded bench setup. The standalone `muhl_interpret.py` is another instrument; the live page does not invoke it.
