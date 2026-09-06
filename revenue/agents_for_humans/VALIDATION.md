# Validation record

The development runs below are synthetic examples on the existing Commons Gemini Code Assist route through actual Strands agents. They are not customer incidents, buyer deliveries, executed fixes, a reliability benchmark, or evidence of time saved or revenue. Token usage is unavailable from the existing relay. Raw local receipts are retained unchanged in `runs/`; `RUN_HISTORY.json` records their exact hashes, source versions, request outcomes and timings without credential values.

| Run ID | Source prefix | Calls | Recorded outcome and substantive interpretation |
|---|---|---:|---|
| `4591332e-fe19-4f80-a8ad-e56a13af0974` | `b39339c3` | 1 | Ordinary case failed closed after an actual provider timeout of 680.253301 seconds. No model output was recovered. This was a timeout, not an operator-aborted request. |
| `57dac963-b455-4bbe-9a2f-a1a0a1a130bc` | `b39339c3` | 2 | Insufficient case requested clarification with no diagnosis. This result belongs to the earlier implementation. |
| `b83eb7df-6465-4c1f-ad2b-a4d6028f930a` | `b39339c3` | 2 | Structurally accepted but **semantically failed** independent inspection: unseen file reversion was labeled observed, confidence was inflated, and the reviewer failed to resolve its own competing account. This is withheld from positive demonstrations and retained as a regression fixture. |
| `34efe41d-4de9-4e76-b3c5-585902e928c3` | `d489dadb` | 2 | Ordinary case failed closed parsing a single enclosing JSON fence in the reviewer output. The draft had improved uncertainty, but no accepted result was released. The old receipt did not persist the exact assembled draft report, so its full reviewer hash cannot be independently reconstructed from this receipt alone. |
| `f566ee09-1682-4f7f-a98c-d0f52f6d01bb` | `d489dadb` | 2 | Insufficient case correctly proposed no diagnosis, but failed closed at the same fenced-output parser boundary. |
| `d816c9e4-f82b-49f8-b5f1-7e22e0c6cd7a` | `b9a03b81` | 2 | Ordinary case was correctly rejected by the reviewer: HIGH confidence contradicted the still-plausible alternative that the unseen test reads source configuration directly. The draft report is retained and withheld. |
| `3492780d-082f-400c-b114-09198837ee42` | `b9a03b81` | 2 | Insufficient case contained no diagnosis and the reviewer accepted it, but an application rule incorrectly required cause counterexamples even though no causes existed. The actual result remains failed closed; its output is a controlled regression for the corrected rule. |

These thirteen actual requests preceded the next revision implementation. Subsequent outcomes must be appended with their actual version and receipt hashes; a successful retry must not replace this history.

The current controlled suite has 41 tests using the real Strands loop and explicitly labeled model doubles. It checks evidence, confidence, review coverage, strict parsing, isolated contexts, provider completion and request accounting, plus a bounded internal revision that retains both versions and obtains a fresh independent review. These tests establish gate behavior, not model accuracy. The one-revision design is a response to actual reviewer rejection, not permission to silently lower confidence or automatically accept a report.
