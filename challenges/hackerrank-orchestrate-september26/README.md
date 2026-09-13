# HackerRank Orchestrate September 2026 — Buy or Wait?

Owner-authorized Swarm-Z build lane: `HACKERRANK-ORCHESTRATE-BUY-WAIT-MNEMOSYNE-Z7314-20260913`.

This directory preserves a submission-shaped implementation for HackerRank Orchestrate September 2026, challenge **Buy or Wait?**, built from the official public starter specification at `interviewstreet/hackerrank-orchestrate-september26`.

## Current evidence

- Builder: Mnemosyne-Z7314 / GPT-5.6 Sol.
- Local submission-layout unit suite: **20/20 PASS**.
- `python3 -m compileall -q .`: **PASS**.
- Packaged `code.zip` SHA-256: `14d34bd3ed129ad98b4ba37bf627fe10c77ee378a891a5256e53d908dd626fa7`.
- Full 250-request official-dataset execution: **NOT CLAIMED** from this seat because the dataset bytes were not mountable in the execution VM.
- The checked-in usage report is deliberately a pre-full-dataset template and must be overwritten by the official run before submission.

## Design

The financial decision path is deterministic. Optional model use is bounded to extracting structured facts from untrusted messages/images; model output cannot directly choose a recommendation. The verifier reconstructs dated cashflows, fixed FX, recurrence, minimum-balance safety, exact installment schedules, two-payment partial plans, and up to three permitted spending changes.

## Run

With the official starter `dataset/` adjacent to `code/`, run from the challenge root:

```bash
python code/main.py
```

Then verify `output.csv` and `code/evaluation/usage_report.md` came from the same final run before packaging/submission.
