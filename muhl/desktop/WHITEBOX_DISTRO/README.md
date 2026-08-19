# White Box

**A desktop instrument for looking inside a model file.**

Point it at a `.gguf` and it reads the parameter **bytes** directly and shows you what is in there: the architecture,
the quantization recipe, per-layer statistics, what individual tokens and neurons mean, and where a file has been
tampered with. Then it lets you **edit** those bytes — reversibly, with a byte-exact undo log.

There is **no inference here.** Nothing is generated, no server is loaded, no GPU is used. White Box opens the file
with `mmap`, reads bounded windows of it, and does the arithmetic in numpy. That is why it works on an 8 GB laptop
against a 70 GB model, and why it only needs two dependencies.

---

## Quickstart

**1. Install Python 3.9+ and the two dependencies.**

```
python -m pip install -r requirements.txt
```

**2. Tell it where your models are.** Pick whichever you prefer — they are checked in this order:

```
# a) environment variable
set WHITEBOX_MODELS_DIR=D:\ai\models          (Windows)
export WHITEBOX_MODELS_DIR=/home/me/models    (macOS / Linux)

# b) a config file: copy whitebox.config.example.json -> whitebox.config.json and edit "models_dir"

# c) do nothing. Start the app, type the folder into the "models folder" box in the header,
#    and click "Set folder". It writes whitebox.config.json for you and remembers it.
```

Check what your machine resolved to at any time:

```
python wb_config.py
```

**3. Run it.**

```
python whitebox_app.py            # http://127.0.0.1:7862   the main instrument (13 tabs)
python fable_whitebox_v2.py       # http://127.0.0.1:7864   the read-only research suite
```

Pick a model from the dropdown (or paste a full path into the box next to it) and click **Import**.

**4. Prove the install works.**

```
python smoke_test.py
```

This builds a small real `.gguf` in a temp folder, starts the actual server on a free port, imports that model over
the real HTTP routes, and checks that the anatomy it reports genuinely describes that file. It touches none of your
models and writes nothing to your config. `PASS`/`FAIL` per check, exit code 0 on success.

To run the same gate against one of your own files:

```
python smoke_test.py --model D:\ai\models\your-model.gguf
```

---

## The first Import is slow. After that it is instant.

Reading a large `.gguf`'s index means parsing its tokenizer, which takes ~25 s on a 40 GB file. White Box does that
**once** and caches the result next to the model as `<model>.gguf.wbindex.json`. Every later read — anatomy, precision
map, tensor statistics — uses the cache and the memmap, so it returns immediately. Delete the sidecar to force a
re-parse. Other sidecars you may see (`.wbvocab.blob`, `.wbgenome`) are the vocabulary cache and the edit-undo log.

---

## What each tab does

The main app (`whitebox_app.py`, port 7862) has thirteen tabs. The first nine are read-only; the four marked **write**
change bytes in the model file and are recorded in the Genome log.

| Tab | What it shows you |
|---|---|
| **Overview** | The anatomy: architecture, parameter count, layer count, hidden size, vocab, expert count, file size, and the histogram of quantization types across every tensor. Start here. |
| **Precision map** | The mixed-quant **recipe** — which tensor *role* (`attn_q`, `ffn_down`, `token_embd`, norms…) was given which precision (Q4_K / Q6_K / Q5_K / F32). This is what the quantizer chose to protect, and it is not shown by standard tooling. |
| **Layers** | Per-layer standard deviation and near-zero percentage for a tensor role you choose, plus a std-vs-depth sparkline. This is where outlier features, dead neurons, and layers that barely move become visible. |
| **Circuitry** | One FFN block read as a **bank of transistors**: per-unit gate gain, drain drive, and rho, plus amplifier / inhibitor / dead counts and a sampled schematic. |
| **System** | Attention read as the model's **IPC bus** — per-head read/write channel strengths and the GQA grouping — mapped onto operating-system primitives (compute, memory, scheduler, bus, storage, I/O codec). |
| **Decompiler** | Bytes to meaning. A token's embedding row to its nearest tokens; **vector arithmetic** (`king - man + woman -> queen`, which is measurably noisier on a quantized table — that noise *is* the cost of quantization); and **bit-edit then measure**: change a token's stored bits and watch its neighbor list change. Reversible. |
| **Tokens** | The reverse direction. Type a token and see which **neurons** of a layer carry that concept, ranked by projection onto the token's stored direction. Also decodes a single parameter to the tokens it points at. |
| **Align** | Build an **alignment axis** from contrasting concept tokens, project the whole vocabulary onto it, and read off the most-aligned and most-anti-aligned tokens — so you can see what the axis actually captured before you use it. **(write)** Then move one token along that axis, reversibly, and measure the before/after. |
| **Tensor scope** | Dequantize any single tensor: mean / std / min / max, sparsity, value histogram, and **quant stress** — per-block outlier magnitude, i.e. where the quantization hurts most. |
| **Search + destroy** | **(write)** Search tensors, tokens, or KV metadata by name or regex, then prune with intent: zero a tensor, remove one MoE expert, scale a tensor, scrub a token. Every action reversible. |
| **Genome** | The byte-exact undo log. Every write any tab made, with revert-last and revert-all. This is what makes the write side safe to experiment with. |
| **Create** | **(write)** Compose a build spec from measured tensor health and the precision recipe, applied as reversible weight edits and reference-based routing rather than a multi-GB copy. |
| **Export** | Scrape everything the White Box can read from one model into a single `.json` + `.md` artifact, and optionally a full **Researcher Archive** folder (raw weight bytes plus all analysis). Written to `out_dir` / `archive_dir`. Runs as a background job. |

### The second UI

`fable_whitebox_v2.py` (port 7864) surfaces the `fable_*` research suite as clickable cards with editable argument
boxes, in three groups: **meaning geometry** (how meaning is arranged in the embedding space, how few bits it needs,
whether that geometry is universal across models), **structure & security** (per-tensor anomaly sweeps, entropy-crater
scans for baked-in circuits, per-row structural localizers), and **forge & circuits** (enumerating circuit structure
found in a file). Each Run launches a child process that ends before its output is rendered, so the server itself
never holds a model open.

---

## Configuration reference

Every setting resolves in this order: **environment variable → config file → auto-discovery.**

| Setting | Environment variable | Default |
|---|---|---|
| `models_dir` | `WHITEBOX_MODELS_DIR` | first existing of `$PFC_ROOT/models`, `<app>/models`, `~/models` |
| `out_dir` | `WHITEBOX_OUT_DIR` | `<app>/whitebox_out` |
| `archive_dir` | `WHITEBOX_ARCHIVE_DIR` | `<out_dir>/research_archive` |
| `default_model` | `WHITEBOX_MODEL` | the first `.gguf` in `models_dir` |
| `clean_model` | `WHITEBOX_CLEAN_MODEL` | `default_model` |
| `titan_model` | `WHITEBOX_TITAN_MODEL` | `default_model` |
| `circuits_registry` | `WHITEBOX_CIRCUITS_JSON` | `<models_dir>/titan_circuits.json` |
| `results_json` | `WB_RESULTS` | `<out_dir>/whitebox_matrix.json` |
| `port` | `WHITEBOX_PORT` | 7862 |
| `port_v2` | `WHITEBOX_PORT_V2` | 7864 |

The config file is searched for as `$WHITEBOX_CONFIG`, then `./whitebox.config.json`, then `<app>/whitebox.config.json`,
then `~/.whitebox/config.json`. See `whitebox.config.example.json`; every key is optional.

Two routes report and change this at runtime: `GET /config` returns everything the app resolved, and `GET /setmodels?dir=...`
is what the **Set folder** button calls.

---

## Notes on the tools that expect specific models

Several tools in the `fable_*` and `pfc_*`/`wf_*` families were written against particular model files and compare
against results measured on them. In this build their model paths are configurable (`titan_model`, `clean_model`), so
they run against whatever you point them at — but a tool that scans for circuit structure will report finding none in
a file that has none, and the `pfc_atlas` census additionally needs a circuit registry JSON (`circuits_registry`) that
is not part of this distribution. Those tools starting up and reporting nothing found is the expected result on a
model that does not contain what they look for.

## What is not in this build

The tools that evaluate a gate netlist on the host are not included: `pfc_atlas_verify.py`, `pfc_forge.py`,
`pfc_langton.py`, `pfc_turing.py`, `pfc_cyclic.py`. Their UI cards have been removed from both interfaces so nothing
offers a button that cannot run. Everything shipped here reads and reports; nothing evaluates gates.

## Safety

The read tabs never write to your model file. The write tabs do — in place, on the actual `.gguf` — and every change is
recorded byte-exactly in the Genome log so it can be reverted. Keep a copy of anything you care about before using the
write side. Exports and archives are written to `out_dir`/`archive_dir` and never into your models folder.

Both servers bind to `127.0.0.1` only.
