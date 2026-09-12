# ASTRA V5 joint-liquidity paired launch

Run the accepted V4 archive and the same archive with only root `frozen_selected.py` replaced. This launcher reuses the existing Commons official-engine evaluator, raw-file loader, and public opponent bank. It does not duplicate their sources or install packages.

Use an existing Linux fleet VM with Python 3.11+ and g++. Supply the VM's existing `revenue/kaggriculture` directory and official-engine cache. The source bank is at `cloud-execution-lab/candidates/v4/research/reference-policy-bank`; its registry checks the unchanged public Apex v7 native/Python source and Arlene v14 source. Apex is compiled once before games, then loaded into a fresh process for each game. Arlene is an ancestor control, not the current leaderboard team policy.

```bash
# Set these to existing VM paths; never substitute a different baseline.
KG=/path/to/commons/revenue/kaggriculture
ENGINE=/path/to/pinned-engine
V4=/path/to/titan-v4-4af11131-rebuilt.tar.gz

curl -fL https://raw.githubusercontent.com/woahwhattheheck/commons/3447b9f1f157aab8a98c0b3a283a7058e477482b/revenue/kaggriculture/cloud-execution-lab/frozen_selected.py -o joint-frozen_selected.py

python3 -B paired.py \
  --kg-root "$KG" --engine-dir "$ENGINE" --baseline "$V4" \
  --overlay joint-frozen_selected.py \
  --overlay-sha256 340149a3d9e68b14440825943a5f98067401c913af42727ac9a3ba5b3d829cc6 \
  --seeds 1209120226,1209120711 --opponents apex_v7,arlene_v14 --seats 0,1 \
  --output astra-joint-liquidity-01
```

The full matrix is 8 pairs / 16 games. For a first 4-pair receipt, use only seed `1209120226`; the second seed can run on another VM with a distinct output directory. To allocate four smaller jobs, split by one seed and one opponent. Keep each V4/candidate pair on the same VM. Each game is sequential within that job, freshly extracts its own archive, and starts new persistent agent processes with private working directories. It runs the complete episode with 719 callbacks; it does not shorten episodes or reuse agent state between games. Initialization through the pinned raw-file loading contract is included in the first timed call.

The default callback RPC deadline is 1.25 seconds, including IPC headroom, and the whole-game bound is 900 seconds. V4's own native deadline remains unchanged. This offline process driver does not reproduce hosted Kaggle resource enforcement. Any callback, opponent-loading, timeout, or interpreter failure is retained in the game JSON and prevents a paired score delta; failures never become zero-score wins. The two variants use the same independent policy RNG seed, game seed, seat, and opponent source. Run order alternates between pairs.

Each finished game writes `<cell>-baseline.json` or `<cell>-candidate.json`; each finished pair writes `<cell>.json`, updates `report.json`, and prints a `PAIR` receipt. Results contain terminal scores, each variant's own-score-minus-opponent-score margin, candidate-minus-baseline margin delta, complete failure details, callbacks, maximum/mean callback and RPC times, CPU/RSS, trace hashes, and archive/engine/source identities. `run.json` retains compiler and opponent preparation receipts. Post raw results in the existing [simulation request thread](https://tokenjunkielabs.slack.com/archives/C0C1F274SGH/p1789206314756639).

Source identities:

- V4 archive SHA256: `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b` (75 members).
- Candidate overlay: [commit 3447b9f1](https://github.com/woahwhattheheck/commons/blob/3447b9f1f157aab8a98c0b3a283a7058e477482b/revenue/kaggriculture/cloud-execution-lab/frozen_selected.py), SHA256 `340149a3d9e68b14440825943a5f98067401c913af42727ac9a3ba5b3d829cc6`.
- Official Kaggle source ref: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`; interpreter blob `3c202c7ee921da239356789e266b694635103fc4`.
- Existing evaluator: `cloud-execution-lab/reference/evaluator/evaluate.py`; loader: `20260907-offline-agent/evaluate.py`; bank bridge: `reference_policies.py` alongside its `REFERENCE-POLICIES.json`.

Local preparation checks passed: Python syntax, actual V4 archive overlay retaining all 75 members, exactly one changed member, unchanged `selected_sell_core.py`, and complete/incomplete/seat-signed margin handling. Competitive game results are produced by the Linux launch, not these preparation checks.
