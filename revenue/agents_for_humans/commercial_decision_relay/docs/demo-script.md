# Demo script (target: 3m 30s)

**0:00–0:25 — Problem.** A closer should not re-read every routine commercial thread. But an agent must not hallucinate "deal closed" from vague prose. Commercial Decision Relay handles the repetitive custody loop and interrupts only for real decisions.

**0:25–0:55 — Architecture.** Show the Strands agent, five deterministic custom tools, hash-only lifecycle audit hooks, and the explicit authority boundary. The model decides which safe tool to call; deterministic code decides evidence status.

**0:55–1:45 — Reproducible fixture.** Run `decision-relay reconcile --batch fixtures/demo-batch.json --output /tmp/receipt.json`. Show four series: exact acceptance, counteroffer, decline, and unanswered offer. Only two are surfaced. Decline/unanswered stay quiet.

**1:45–2:20 — Product board.** Run `python -m decision_relay.web_demo --batch fixtures/demo-batch.json`. Show the decision cards and the all-false authority footer.

**2:20–2:55 — Tamper resistance.** Verify with the independently supplied receipt digest. Change source evidence or the expected digest and show verification fail closed. Mention hostile tests for future evidence, late response, thread/counterparty mismatch, stale offer version, forged authority, and replay.

**2:55–3:25 — Strands live path.** With configured Bedrock or OpenAI provider, ask: "Process the evidence and show only decisions." Show the agent calling `ingest_batch`, `reconcile_evidence`, then `decision_queue`; briefly show hash-only audit JSONL.

**3:25–3:40 — Why it matters.** The closer gets fewer interruptions without surrendering commercial authority to the model. It is a professional agent designed to quietly do work and surface only real decisions.
