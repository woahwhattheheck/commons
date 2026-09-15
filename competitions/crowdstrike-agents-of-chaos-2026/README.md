# Agents of Chaos Act 3 — offline manual prompt-efficiency workbench

This is a **manual-entry, offline-only** analysis aid for CrowdStrike's *AI Unlocked: Agents of Chaos* Act 3, *The Basilisk*. It never logs in, opens the game, submits prompts, calls a contest API, reads network traffic, or computes sponsor-side scores.

Official sources:

- Official rules: https://www.crowdstrike.com/en-us/legal/ai-unlocked-agents-of-chaos-contest/
- CrowdStrike contest overview: https://www.crowdstrike.com/en-us/blog/agents-of-chaos-immersive-ai-security-challenge/

As verified on 2026-09-15, the official rules say Act 3 runs September 15–29, 2026, successful completion plus prompt efficiency drives scoring, and the Act 3 prize is $70,000. The rules permit creative prompt injection against the contest chatbot but prohibit scoring-system attacks, backend exploitation, multiple accounts/account-data manipulation, automated tools or bots interacting with the system, network interception/modification, and access to other players' data/accounts. **The rules, not this README, govern.**

## What the workbench does

`workbench.py` validates strict operator-entered attempt records and deterministically produces a per-puzzle review frontier. Only successful records are ranked, and only the `observed_tokens` integer typed by the operator is used. The workbench intentionally does **not** implement a tokenizer, infer token counts, or claim equivalence to CrowdStrike's score.

Each attempt must self-attest that it came from the registered account, is original English-language work using standard gameplay mechanics, and must explicitly declare all prohibited-action flags `false`. A declared prohibited action is rejected rather than summarized. Output authority is always `SELF_ATTESTED_ONLY`; it is not a sponsor eligibility/compliance certificate.

Outputs are deterministic for the same logical ledger regardless of attempt-array order:

- `frontier.json` — canonical packet, source ledger hash, per-puzzle successful frontier, duplicate-prompt observations, and packet receipt hash;
- `frontier.md` — human review rendering;
- `receipt.sha256` — packet receipt digest.

Publication creates a **new bundle directory** and refuses to overwrite an existing directory. The output parent is assumed to be operator-controlled local storage; this tool does not claim an adversarial filesystem sandbox.

## Use

```bash
python competitions/crowdstrike-agents-of-chaos-2026/cli.py summary \
  competitions/crowdstrike-agents-of-chaos-2026/example-ledger.json

python competitions/crowdstrike-agents-of-chaos-2026/cli.py compile \
  competitions/crowdstrike-agents-of-chaos-2026/example-ledger.json \
  --out-dir /tmp/aoc-review-bundle

python competitions/crowdstrike-agents-of-chaos-2026/cli.py verify \
  competitions/crowdstrike-agents-of-chaos-2026/example-ledger.json \
  /tmp/aoc-review-bundle/frontier.json
```

Run the hostile suite in ordinary and optimized Python:

```bash
python -B -m unittest -q competitions/crowdstrike-agents-of-chaos-2026/test_workbench.py
python -O -B -m unittest -q competitions/crowdstrike-agents-of-chaos-2026/test_workbench.py
```

## Authority ceiling

No registration or terms acceptance; no login/MFA; no live gameplay or prompt submission; no automated interaction; no scoring/backend probing; no traffic interception; no multi-accounting; no other-player access; no vulnerability exploitation; no prize, payment, eligibility, sponsor-compliance, or revenue claim. Any live contest participation remains a human/manual action governed by CrowdStrike's official rules.
