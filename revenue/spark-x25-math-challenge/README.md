# SOL-SPARK — Spark-X2.5 math challenge harness

Paid-work focus: [XHToken/Spark-X2.5 issue #9](https://github.com/XHToken/Spark-X2.5/issues/9), HER Hack-Astron #6. The event advertises one USD 100 winner prize and requires a real, reproducible Spark-X2.5 math evaluation. Submission closes 2026-09-13 24:00 Beijing time (UTC+8).

**Status:** harness published; no model result is claimed by this directory until a GPU run receipt lands. Do not invent or backfill outputs.

## Study

Run the official `XHToken/Spark-X2.5-1.7B` checkpoint on one deterministic 128-item sample of the public GSM8K test split under two prompt conditions:

1. `direct` — request only `FINAL: <number>`.
2. `reason` — request a concise, checkable derivation and the same final-answer line.

Both conditions use the same dataset revision, sampled indices, sample seed, model revision, temperature 0, top-p 1, and per-item generation seed sequence. This makes the prompt-format comparison paired and reproducible. Raw API responses are retained; unparseable outputs count as wrong.

The harness records the exact question, gold answer, full prompt, full assistant output, raw OpenAI-compatible API response, token counts, latency, parse route, correctness, output hash, environment versions, GPU receipt, selected indices, and SHA-256 digests of the harness and evidence files. It intentionally does **not** record environment variables, credentials, hostname, working directory, or Hugging Face cache paths.

## Pin revisions first

Use the exact revision SHAs in every run and final write-up.

```bash
python - <<'PY'
from huggingface_hub import HfApi
api = HfApi()
print("MODEL_REVISION=" + api.model_info("XHToken/Spark-X2.5-1.7B").sha)
print("DATASET_REVISION=" + api.dataset_info("openai/gsm8k").sha)
PY
```

Record those two values before downloading or running anything.

## Serve Spark-X2.5

The upstream Spark-X2.5 repository documents vLLM as a supported inference path. Download the pinned checkpoint, then start a local OpenAI-compatible server. Keep the exact `vllm --version`, container/image tag if any, GPU type, precision/quantization, and server command in the final report.

Illustrative local commands:

```bash
hf download XHToken/Spark-X2.5-1.7B \
  --revision "$MODEL_REVISION" \
  --local-dir ./models/Spark-X2.5-1.7B

vllm serve ./models/Spark-X2.5-1.7B \
  --port 30000 \
  --trust-remote-code \
  --served-model-name spark25 \
  --gpu-memory-utilization 0.80 \
  --max-model-len 8192 \
  --enable-prefix-caching \
  --chat-template ./models/Spark-X2.5-1.7B/chat_template.jinja
```

If a different supported runtime or quantization is used, disclose it and do not compare its numbers as though they came from the command above.

## Run the paired evaluation

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python eval_gsm8k.py \
  --model-revision "$MODEL_REVISION" \
  --dataset-revision "$DATASET_REVISION" \
  --prompt-mode direct \
  --sample-size 128 \
  --sample-seed 20260908 \
  --generation-seed 20260908 \
  --output-root runs-direct

python eval_gsm8k.py \
  --model-revision "$MODEL_REVISION" \
  --dataset-revision "$DATASET_REVISION" \
  --prompt-mode reason \
  --sample-size 128 \
  --sample-seed 20260908 \
  --generation-seed 20260908 \
  --output-root runs-reason
```

Each invocation refuses to reuse an existing run directory. A partial/crashed run is evidence of a failed attempt, not a completed benchmark; preserve it separately and start a clean output root for a replacement run.

## Required return bundle

A GPU runner should return, for **both** prompt modes:

- `manifest.json`
- `raw.jsonl`
- `summary.json`
- the exact model and dataset revision SHAs
- the exact server command
- `vllm --version` (or equivalent runtime version)
- GPU model, precision/quantization, and whether the GPU was paid or free
- any startup/server log needed to substantiate the run

Before publication, verify `summary.json`'s `raw_jsonl_sha256` against the returned `raw.jsonl`.

## Final submission checklist

The challenge requires publication in the Hugging Face Discussion for the model actually tested, followed by a GitHub issue reply linking that Discussion. The final write-up should include:

- exact model + dataset revisions and acquisition source
- runtime/hardware/precision/quantization
- all decoding parameters and random seeds
- sample size, split, exact scoring rule, parse-failure treatment
- direct vs reason accuracy and token/latency trade-off
- representative complete `reason` successes and failures selected by a declared rule, not cherry-picking
- at least one inspection for a right-answer/wrong-reasoning case
- links to the scoring harness and sanitized raw evidence
- license/source attribution for Spark-X2.5 and GSM8K
- explicit AI-assistance disclosure
- no Hugging Face tokens, personal cache paths, private data, intranet addresses, or model-weight uploads

Do not claim the USD 100 prize is earned merely by submitting; it is a judged winner award.
