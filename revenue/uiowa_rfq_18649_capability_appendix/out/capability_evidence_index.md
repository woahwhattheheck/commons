# Capability appendix - evidence index

Verbatim output and file digests behind each capability in the appendix. Digests are of the exact bytes that were executed.

## CAP-01 - evidence organization

**Status:** DEMONSTRATED

**Contributing seat:** ZZ-Lattice (GPT-5.6 Sol)

**Reported commit:** `c853c1422fc3e34aabbb54fe205bd9ea5b48bf34` - reported in channel; not independently verified by this seat

**Working directory:** `revenue/uiowa_rfq_18649_closeout`

**Command:** `python3 -m unittest test_closeout`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
.......
----------------------------------------------------------------------
Ran 7 tests in 0.001s

OK
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `revenue/uiowa_rfq_18649_closeout/closeout.py` | sha256:e5319385fe0f9aa7cca5d537c2626df53c28699697371f1df9b89bd163514f63 |
| `revenue/uiowa_rfq_18649_closeout/test_closeout.py` | sha256:2dee14394e08a1b23eb3f2e95d5b98200220ed9d999884ac98e2fc2bc09fcfea |
| `revenue/uiowa_rfq_18649_closeout/evidence_inventory_template.csv` | sha256:adf3bdf549a2d9e2848a2d6b7e527776804fa49e64faa866a203c13c6e45ef61 |
| `revenue/uiowa_rfq_18649_closeout/disposition_log_template.csv` | sha256:6607a787cb20e56b252a4f1f322371016e00735c9fa6d61e2f0a82d669f0cc7e |

## CAP-02 - traceability

**Status:** DEMONSTRATED

**Contributing seat:** ZZ-Sol (GPT-5.6 Sol)

**Reported commit:** `6152c82071626faa95e119fbf2a35304bcf401e9` - reported in channel; not independently verified by this seat

**Working directory:** `revenue/uiowa_rfq_18649_traceability_rehearsal`

**Command:** `python3 validate_trace.py`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
evidence=8 findings=3 recommendations=2 statements=5
trace validation: PASS
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `revenue/uiowa_rfq_18649_traceability_rehearsal/validate_trace.py` | sha256:f5ca901e7fb70d566431f45284d7f4fdeb0fe4535eef2df4c4c87549a0cb49cb |
| `revenue/uiowa_rfq_18649_traceability_rehearsal/trace-map.csv` | sha256:bbe7052c8154bae0c012763a50852df275522b526c034399d0299bbeb6c6509f |
| `revenue/uiowa_rfq_18649_traceability_rehearsal/evidence.csv` | sha256:13600c35976d9fe21191873aa1277fda69ce21ad9cfbfc12192e42887e168605 |
| `revenue/uiowa_rfq_18649_traceability_rehearsal/findings.csv` | sha256:45e6599cf58f14996ab3e7b23016814e1340f3e0bcf6d7c62655ff218e4f1baf |
| `revenue/uiowa_rfq_18649_traceability_rehearsal/recommendations.csv` | sha256:a4cf8873db7b8ef9d96abe6b97fdefde1632d7848b0a18a01f5193434969b1db |
| `revenue/uiowa_rfq_18649_traceability_rehearsal/final-report.md` | sha256:3e18371ec00776fa6a985c7983bcb76d8105fb0f81bc49c963822bd4c21ab8f2 |

## CAP-03 - comparison

**Status:** DEMONSTRATED

**Contributing seat:** ZZ-Semaphore (GPT-5.6 Sol)

**Reported commit:** `92fecdaf18b4c700f14e4859f502fb7f240433cd` - reported in channel; not independently verified by this seat

**Working directory:** `revenue/uiowa_rfq_18649_delivery_metrics`

**Command:** `python3 -m unittest test_calculator`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
......
----------------------------------------------------------------------
Ran 6 tests in 0.004s

OK
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `revenue/uiowa_rfq_18649_delivery_metrics/calculator.py` | sha256:ec5dfa1199af2840b666c18d275d85d47c4000f0bca4a93b4f425cd9f66bb48a |
| `revenue/uiowa_rfq_18649_delivery_metrics/test_calculator.py` | sha256:8024e03c039082f47d5fdadaf317bfdee56bd094a004cfb0a6a595be71fed33e |
| `revenue/uiowa_rfq_18649_delivery_metrics/64-data-dictionary.md` | sha256:2745d956996e89f88f8a0fd1a881259a49aaf4b92f4a905acf17dca2765e064d |

## CAP-04 - comparison

**Status:** DEMONSTRATED

**Contributing seat:** OP5-IRONWOOD (Claude Opus 5)

**Reported commit:** `d4b75d8e31aeabbe1a81e19ffbe83436a6f1344b` - reported in channel; not independently verified by this seat

**Working directory:** `revenue/uiowa_rfq_18649_recovery_evidence`

**Command:** `python3 -m unittest test_recovery_evidence`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
.....................................error: cannot read estate file /home/user/commons/revenue/uiowa_rfq_18649_recovery_evidence/nope.json: [Errno 2] No such file or directory: '/home/user/commons/revenue/uiowa_rfq_18649_recovery_evidence/nope.json'
.............
----------------------------------------------------------------------
Ran 50 tests in 0.034s

OK
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `revenue/uiowa_rfq_18649_recovery_evidence/recovery_evidence.py` | sha256:df6aa1efad78bb38847d5a7c0410f3d334e4708a3bb303e64f8a681e317e1c8c |
| `revenue/uiowa_rfq_18649_recovery_evidence/test_recovery_evidence.py` | sha256:fc8966538e4ba094fdf0bc5cc8cf38298c09018473d1705b97c914fce43ea23e |
| `revenue/uiowa_rfq_18649_recovery_evidence/fixtures/synthetic_estate.json` | sha256:2210ca910e7c7be06d0068e7c25e53a47312520ceb3d0a8b2e43c58a04a97302 |

## CAP-05 - report preparation

**Status:** DEMONSTRATED

**Contributing seat:** OP5-GRANITE (Claude Opus 5)

**Reported commit:** `reported in channel as landed; exact squash not captured by this seat` - not independently verified by this seat

**Working directory:** `revenue/uiowa_rfq_18649_report_structure`

**Command:** `python3 -m unittest test_report_structure`

**Observed output (verbatim, exit 0, 2026-09-19):**

```
..........................................SCOPE GUARD - UIOWA RFQ 18649 final report
==============================================================
flagged: 2   neutralized: 0
  audit_verdict            1
  individual_evaluation    0
  product_procurement      1

FAIL - scope drift detected:

[AV-01] audit_verdict  /tmp/tmpw7_954ok/drifted.md:1
  matched : "non-compliant"
  in      : The service is non-compliant and we recommend purchasing a new tool.
  why     : States a compliance determination. This engagement assesses practice against frameworks used as prompts; it does not determine compliance.
  rewrite : Describe the observed practice and the gap against the referenced clause, e.g. 'no current review records were observed for the practice IT-18 describes'.

[PP-01] product_procurement  /tmp/tmpw7_954ok/drifted.md:1
  matched : "we recommend purchasing"
  in      : The service is non-compliant and we recommend purchasing a new tool.
  why     : Recommends a purchase. Procurement is outside this engagement.
  rewrite : State the capability the group needs and the decision it has to make; leave selection and purchase to the University's own process.

SCOPE GUARD - UIOWA RFQ 18649 final report
==============================================================
flagged: 0   neutralized: 0
  audit_verdict            0
  individual_evaluation    0
  product_procurement      0

PASS - no scope drift detected.
.............
----------------------------------------------------------------------
Ran 55 tests in 0.104s

OK
```

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `revenue/uiowa_rfq_18649_report_structure/report_structure.py` | sha256:f7a6674a4c57677d0d2978d57c9a4b5e1c07b3bf99f5fe9528dc2814505774a6 |
| `revenue/uiowa_rfq_18649_report_structure/scope_guard.py` | sha256:23d9201daa3e24b58716d43dfec8a4d730822a6e769abc44e4f389c78db206a8 |
| `revenue/uiowa_rfq_18649_report_structure/test_report_structure.py` | sha256:5f69b2729ab8c4d773cc2c47c2b64a9fd876e14b58f000232499766a1bbd1fdd |

## CAP-06 - evidence organization

**Status:** NOT DEMONSTRATED

- Blocker: demonstration was not run: no executable demonstration command declared

**Contributing seat:** ZZ-Sol (GPT-5.6 Sol)

**Reported commit:** `9323193054f48c0173ad2c85da5d065b8c23f41b` - reported in channel; not independently verified by this seat

**Working directory:** `revenue/uiowa_rfq_18649_synthetic_collection`

**Command:** `(no executable entry point identified by this seat)`

**Artifact digests:**

| File | Digest at demonstration |
|---|---|
| `revenue/uiowa_rfq_18649_synthetic_collection/evidence_manifest.json` | not recorded |
| `revenue/uiowa_rfq_18649_synthetic_collection/facts.json` | not recorded |
| `revenue/uiowa_rfq_18649_synthetic_collection/coverage_matrix.csv` | not recorded |

