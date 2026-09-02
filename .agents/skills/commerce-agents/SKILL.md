---
name: commerce-agents
description: >
  Adopt Anthropic's open Claude Commerce Agents blueprint
  (github.com/anthropics/commerce-agents): a shopping agent a business
  embeds for customers, and a merchant agent staff use for back office.
  Use when Bryce says BIG AND HUGE / "We need to use that" with the
  ClaudeDevs commerce-agents screenshot, or when a peer needs the
  clone URL, verticals, or plugin without reminting AutoGTM.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  pin: fd4d59224ab96b43c6dc6888207c67b3bd5a24cf
---

# Claude Commerce Agents

Owner 2026-09-02 hub `1788388313.281509` + `1788388319.646839`: BIG AND HUGE, then "We need to use that." Screenshot is ClaudeDevs open-sourcing commerce agents: `$ git clone github.com/anthropics/commerce-agents`.

Public repo: https://github.com/anthropics/commerce-agents pin `fd4d59224`. Apache-2.0. Cite the clone; do not copy the blueprint source onto Commons.

Door: [commerce-agents.html](../../../commerce-agents.html).
Engine: [host/commerce_agents.py](../../../host/commerce_agents.py).

## Do this

1. Name the public mechanism: clone the blueprint, shopping agent + merchant agent, four verticals (retail, travel, telecom, entertainment).
2. Run `python3 host/commerce_agents.py --json`.
3. Keep AutoGTM leftover and `autogtm.html`. This is not Explee.
4. Checkout in the blueprint hands off to the host. Do not invent Stripe Payment Links. `ANTHROPIC_API_KEY` FINDER-FAILED is a measurement, not a freeze.

## Do not

Add login to the door. Remint `.agents/skills/autogtm` or `host/autogtm_same_loop.py`. Dump `marketplace.html`. Steal Origin `/market`. Fire `--send` / `--go` / `--live`. Spawn Muse Spark / gpt-6 / gpt-5.7 from the other posts in that screenshot. Write a legal memo. Invent ToS numbers.

## Receipt

`python3 -m unittest test_commerce_agents.py` green. `p/cursor-claude-commerce-agents-20260902-01.md` on current main.
