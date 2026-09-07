# RustChain #100: correct contributor setup

Contributor: **woahwhattheheck**. RTC wallet name: **woahwhattheheck**.
AI disclosure: Bryce's authorized ChatGPT agent performed the source review, documentation edit, checks, and publication in Chat mode.

## Deliverable and reward

This is one documentation improvement under [rustchain-bounties #100](https://github.com/Scottcjn/rustchain-bounties/issues/100), not a discovery-bonus claim. The sponsor advertises **10 RTC tokens for an accepted improvement PR, subject to scope/impact and sponsor review**. This is not a USD reward, a payment reservation, or an acceptance notice.

The completed [patch](contributor-setup.patch) changes only the Development Setup section of upstream `CONTRIBUTING.md`. It corrects the clone-your-fork example, removes the misleading universal npm/Cargo setup path, and supplies a dependency-free, offline Python smoke check with its exact scope and expected result. The root npm manifest has no `test` script and there is no root `Cargo.toml`. No runtime code, dependency files, payment workflows, or bounty-board README are changed.

This repository hosts the public deliverable through the sponsor's [accepted 403 submission route](https://github.com/Scottcjn/rustchain-bounties/blob/9ef595b315709cd2c9610a5092b40417288dfa8b/docs/HOW_TO_SUBMIT_A_BOUNTY.md#if-you-cant-comment-403-resource-not-accessible-by-integration). The GitHub integration rejected the upstream intake comment with `403 Resource not accessible by integration`. Publication here, including any Commons PR merge, **does not mean the sponsor repository has merged or paid for this change**. Upstream filing, acceptance, and payment require the sponsor's actual receipt.

## Source provenance

Reviewed upstream commit: [`9ef595b315709cd2c9610a5092b40417288dfa8b`](https://github.com/Scottcjn/rustchain-bounties/commit/9ef595b315709cd2c9610a5092b40417288dfa8b).

| Source at that commit | Verified Git blob ID |
| --- | --- |
| [CONTRIBUTING.md](https://github.com/Scottcjn/rustchain-bounties/blob/9ef595b315709cd2c9610a5092b40417288dfa8b/CONTRIBUTING.md) | `5410f4b4a11586f8498ed5297051b45045d54c13` |
| [package.json](https://github.com/Scottcjn/rustchain-bounties/blob/9ef595b315709cd2c9610a5092b40417288dfa8b/package.json) | `dab6120e530043509b8aad1eba5b6c71115ad091` |
| [agent_framework/bounty_claimer.py](https://github.com/Scottcjn/rustchain-bounties/blob/9ef595b315709cd2c9610a5092b40417288dfa8b/agent_framework/bounty_claimer.py) | `5f64c0b8bab9315f13041a891ab5fb23fa0f05e9` |
| [tests/test_bounty_claimer.py](https://github.com/Scottcjn/rustchain-bounties/blob/9ef595b315709cd2c9610a5092b40417288dfa8b/tests/test_bounty_claimer.py) | `01014c55e1eb09ba107ff57a7d95169009c1e690` |

Patch SHA-256: `8018498acf01e9fc3f81e0396cee25466615051cfcaf39f2d685f4ebfcd9d5db`.
Expected `CONTRIBUTING.md` Git blob after applying: `532f2d5d4b57de0a8861d96a6f3f99d1af86a6fe`.

## Executed checks

The [execution receipt](checks.txt) records the actual commands and output. Checks used an isolated Linux Chat runtime and exact connector-read source fixtures, each verified against its Git blob ID. The environment was not presented as a full repository clone.

- Baseline `npm test --offline --ignore-scripts`: exit 1, `Missing script: "test"`.
- Exact command extracted from the new Markdown, in a fresh Python 3.13.5 venv created with `--without-pip`: **2 tests passed**, including the CLI-failure case. No third-party dependencies or credentials were installed.
- `git diff --check`, forward apply, reverse apply, and byte-for-byte round-trip checks: passed. Only `CONTRIBUTING.md` differs; the rest of that file is unchanged.

These are documentation validation results, not a claim that a full build, every component, the real GitHub CLI, or live node integrations were tested. The unchanged existing tests exercise the real formatter and error handling while mocking the external `gh` subprocess.

## Reproduce against a full upstream checkout

Save `contributor-setup.patch` next to the checkout directory, then run:

```bash
git clone https://github.com/Scottcjn/rustchain-bounties.git
cd rustchain-bounties
git checkout 9ef595b315709cd2c9610a5092b40417288dfa8b
git apply --check ../contributor-setup.patch
git apply ../contributor-setup.patch
python3 -m unittest discover -s tests -p 'test_bounty_claimer.py' -v
git diff --check
git hash-object CONTRIBUTING.md
```

The clone and remote-fork operations above were not executed successfully in the Chat runtime because its network DNS was unavailable. Source reads used the connected GitHub integration; patch application and the documented test command were actually executed locally.

Supply-chain proof: no dependency changes, installations, blind shell downloads, new runtime code, or external executables are introduced by the upstream patch. Source revision and artifact checksum are pinned above. The target upstream repository's licensing terms continue to apply to the patch.
