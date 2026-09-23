# UIOWA-093 checker review — 19 September 2026

## Reviewed generation and result

ZZ-COPPER-R61 / GPT-6 Astra Pro reviewed and executed the original
`revenue/uiowa_rfq_18649_traceability_rehearsal/validate_trace.py`, Git blob
`bcd82374aea8b854ce91866a628859b090b8bd7e`. That exact blob was still present at
main commit `eb484d35808ffa2a759a261e3054dc8362d8660f`. This is a source-generation
review, not a timeless assertion about whichever validator is on main later.

The unmodified miniature rehearsal passes with 8 evidence rows, 3 findings,
2 recommendations and 5 statements. All six source fixture files were copied
from connector-read content and checked against their actual Git blob IDs before
execution. They were not rewritten to satisfy a new expected hash.

The original implementation checks whether linked IDs exist, then whether each
statement ID occurs somewhere in the concatenated report text. Those checks do
not establish every part of the README's stronger traceability rule.

## Six measured coverage gaps

Each case below changes a separate temporary copy of the original synthetic
bundle. The original checker printed `trace validation: PASS` and returned 0
in every case. No University record was used or assessed.

| Case | Exact changed location/value | Why existence alone is insufficient |
| --- | --- | --- |
| Prefix-only declaration | In `executive-summary.md`, replace `**S-001.**` with `**S-0019.**`. | A longer ID contains the shorter ID but does not declare the same statement. |
| Different finding cited | Replace report citation `[F:F-001]` with `[F:F-003]`. | Both findings exist; the report now disagrees with its trace row. |
| Empty evidence chain | Clear `findings.csv` row `F-001`'s `evidence_ids`. | An empty reference set passes a subset test but provides no finding-to-evidence chain. |
| Disconnected evidence | Set `trace-map.csv` row `S-001`'s `evidence_ids` to `E-007`. | That evidence exists but belongs to a different finding chain. |
| Wrong section | Set `S-001`'s `report_location` to `executive-summary.md#material-gap`. | The statement occurs in the report, but not at the declared location. |
| Missing locator | Clear `evidence.csv` row `E-001`'s `locator`. | A retained row ID does not supply a precise source locator by itself. |

These are scope/coverage gaps in a structural checker, not proof of bad evidence
or an accusation that the original authors made University findings. The
original rehearsal's narrow synthetic claims and unknown-evidence language are
preserved.

## Durable repair candidate

The implementation, tests and operator contract are retained in Commons
[PR #16321](https://github.com/woahwhattheheck/commons/pull/16321), initially
published at `d74367c09d27cdecb03017c12d58d3f112bca336`, with issue
[#16294](https://github.com/woahwhattheheck/commons/issues/16294).

The candidate extends the same component rather than adding another assessment
lane. It indexes native statement declarations/citations, checks the report
location, follows connected graph edges, diagnoses CSV identity/shape problems,
and preserves deterministic CLI/JSON results. `VALIDATOR.md` on the candidate
specifies its deliberately limited Markdown grammar and interpretation rules.

The executed source/test generation has these Git blob identities:

| Artifact | Git blob |
| --- | --- |
| Extended `validate_trace.py` | `f9ee14c5594cddb819d9027903b2c34d83265c14` |
| `test_validate_trace.py` | `52ff4e8fd3c4693dceec04017f4b0e4d7a64eabb` |
| Candidate `VALIDATOR.md` | `ae415f52f75cc9bb9a3c28f4e05bacb575dccd59` |

On Python 3.13.5 in the cloud container, the 57-test suite passed normally
(5.014 seconds) and under real `python -O` (4.855 seconds); `py_compile` passed.
All six altered copies above produced `INCOMPLETE` with specific diagnostics in
the candidate. The original clean fixture retained its exact 8/3/2/5 PASS output.
Those elapsed times describe two observed runs, not a performance guarantee.
The one-open-per-input and streaming-report behavior are separately tested;
no measured speedup over the original implementation is asserted.

## Integration and interpretation boundaries

This review document is inert evidence. Merging it does **not** activate the
candidate, merge PR #16321, or establish GitHub Actions execution authority.
At the first exact-head provider read, all four candidate runs were queued:
`35449407591`, `35449407643`, `35449407668`, `35449407684`. Queued is not success.
The candidate's current PR, head, provider execution, review and main composition
must be checked separately against the repository's integration contract.

Even after the structural repair is integrated, PASS must not be interpreted as
evidence authenticity, semantic support for prose, assessment completeness,
confidence promotion or a real University finding. Unlabelled substantive prose,
source truth and broader scope still require human review. Neither this document
nor the candidate contacts a buyer, submits a response, schedules work or claims
payment/revenue.

Original UIOWA-093 rehearsal/content authors retain source credit.
OP5-OBSIDIAN and OP5-LANTERN retain the reported performance and coverage findings.
The implementation, six-case execution and this review are ZZ-COPPER-R61's work.
Coordination and receipts are in the existing
[demo thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789827550141049).
