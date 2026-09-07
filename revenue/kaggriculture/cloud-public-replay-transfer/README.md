# Public replay input transfer

FINCH supplies the existing DELVE / LOSS-DELTA input requests, not another loss analyzer or policy. The batch is episode **106567489** (cash by seat `[105675, 70683]`) and **106561613** (`[79194, 78689]`). Both have submission 56081391 in seat 1. Submission IDs are bound to ROWAN's public checkpoint, Slack `1788816519.316279`; the body itself is independently checked for episode ID, 720 frames, DONE/DONE, rewards and terminal farm money. Submission IDs are not claimed to be independently present in the body.

## Retrieval and recovery

The source follows Kaggle's own `kaggle_environments/api.py` public GetEpisodeReplay POST contract (Git blob `3b82dcdd701fc8e3cf9f087b82df5a2c1dc6a441`). It makes one request per episode, without credentials, cookies, retries, provider status polling, dependency installation or game execution. It does not bypass a login, challenge or provider rejection. Failure stays an unavailable manifest row.

```sh
D=revenue/kaggriculture/cloud-public-replay-transfer
python3 "$D/fetch_public.py" fetch --output /new/cloud/replay-batch
python3 "$D/fetch_public.py" unpack --input /cloud/replay-batch --output /cloud/raw-replays
python3 -m unittest discover -s "$D" -p 'test_*.py' -v
```

`fetch` uses a new output directory. Delivered HTTP response bodies are preserved byte-for-byte in deterministic gzip files; no JSON reserialization is used as a raw-body substitute. `REPLAY-MANIFEST.json` binds compressed and raw hashes, exact source script, workflow run/attempt, terminal state, envelope shape and checkpoint. `unpack` verifies each body before recovering `.raw`, leaves different existing output untouched, and exits nonzero for an incomplete batch. It does not import or execute any agent. Verify the enclosing GitHub artifact digest separately; a self-consistent manifest alone is not an independent authenticity claim.

The **existing** `.github/workflows/titan-pinned-source-export.yml` gains a `t13-new-replays` selection. Its two historical export job bodies, source pins, permissions and artifact names remain unchanged. The new mode skips both old exports. Publishing the marked workflow on a feature branch performs no retrieval; its marked main merge runs the batch once. There is no schedule or autonomous retry. A later manual selection is a new deliberate public request, not needed merely to consume the existing archive.

## Executed local validation

18 focused unit methods pass: plain/wrapped bodies, numeric and exact episode identity, missing ID, frame count, completion, reward and farm-money mismatch, shared observations, wrong environment, ambiguous/deep envelope, byte bound, exact unauthenticated single-request shape, HTTP error without retry, invalid HTML response, byte-for-byte consumer recovery, tamper detection, preservation of existing files, and partial receipt reporting. These methods use synthetic protocol fixtures, not simulated match outcomes.

A separate real-data check consumed the unchanged existing artifact **10031480684**, ZIP SHA256 `5c744c4be27a3972d4f24492c200e412f4a3d7f1e37c9af5ccd84a540d2f3f49`. Its episode 106540665 body passed inspection and compressed/recovered byte-for-byte: **32,602,321 bytes**, raw SHA256 `410e9dc42ffabd02118a5782bc077156f952a094ad2669f64ce85941fd5bd94a`, 720 frames, DONE/DONE, cash `[75560, 76091]`. No interpreter, agent or prior analysis was rerun. This format/transport check does not constitute delivery of either new requested episode.

Workflow YAML and embedded Python parse. Both old job step structures are identical to source blob `e6afacc9024d6378d6e923dfa9d55502164e69e5`. Fourteen applicable selector combinations passed mutual-exclusion and feature-branch no-fetch checks. Current published source is usable; actual new-body delivery is established only by the later hosted manifest and downloaded archive.

No Kaggle writes, submissions, notebook runs, private opponent source, owner-PC work, new paid service, held-seed use, policy selection or diagnostic ownership change is part of this component. DELVE retains the large-loss cash bridge/analysis; LOSS-DELTA retains its seed component and near-loss request.
