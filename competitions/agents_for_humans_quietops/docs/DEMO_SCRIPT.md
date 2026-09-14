# QuietOps demo script (target: 3:30–4:15)

**0:00 — Problem**
“Owners get buried in tiny judgment-heavy tasks. Existing agents either become another inbox or become too willing to act. QuietOps makes routine evidence work disappear, but reserves real decisions for the human.”

**0:25 — Architecture**
Show the Mermaid diagram. Point out the Strands Evidence Auditor and Planner, then the deterministic authority gate outside the model.

**0:55 — Autonomous case**
Open `demo/inbox.json`: two retained source hashes, expected 6625 cents, observed 3750 cents. Run:

```bash
PYTHONPATH=. python -m quietops.cli demo/inbox.json --out /tmp/result.json
```

Show `AUTONOMOUS_REVERSIBLE`, variance `-2875`, `OWNER_REVIEW_VARIANCE`, the content-addressed receipt, and the deterministic `RECONCILIATION_VARIANCE_DECISION` follow-up card. Explain that reconciliation was automated; the discovered discrepancy is what gets escalated; no money moved.

**1:45 — Receipt tamper**
Change one output number and run a small verifier snippet or the unit test. Show verification fails.

**2:15 — Human boundary**
Run `demo/human_required.json`. The task asks to send a customer a $3,500 offer. Show `HUMAN_DECISION_REQUIRED`, reasons for customer contact + money-bearing item + external effect, and `receipt: null`.

**2:55 — Strands layer**
Show `quietops/strands_app.py`: explicit `@tool`s, specialized agents-as-tools, and root QuietOps Agent. Emphasize that `execute_reversible_work()` calls the deterministic gate again, so the model cannot promote its own authority.

**3:35 — Impact**
“Use the same pattern for bookkeeping review, job closeout, inbox triage, compliance evidence, vendor reconciliation, or internal operations. Owners only get pinged when there is a real decision.”
