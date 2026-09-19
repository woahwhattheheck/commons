# Technical capability appendix

Every capability below is bound to working files in this repository and to a run of those files that was executed and recorded. A claim that could not be bound is not described here as a capability; it is listed at the end with the reason. Exact file digests and verbatim run output are in the accompanying evidence index.

## Evidence organization

**CAP-01.** Engagement evidence is held as an itemised inventory in which every item carries a disposition, a retention date, and a written confirmation record, and the completeness of that record set is checked by a program rather than by reading it.

*Why it matters:* At closeout a client asks what you held, what was returned or destroyed, and on what date. This answers that from records instead of from memory, and the check fails if an item is missing one of those fields.

*Demonstrated by:* `revenue/uiowa_rfq_18649_closeout` (4 files). Run `python3 -m unittest test_closeout` from that directory; observed 2026-09-19, result `Ran 7 tests in 0.001s - OK`.

## Traceability

**CAP-02.** Every statement in a finished report can be followed back through the finding it rests on to the source record and evidence file it came from, and a link that does not resolve fails the check instead of passing quietly.

*Why it matters:* When a reviewer disputes one sentence in a report, the underlying record can be produced in one step rather than reconstructed. The same check catches a citation that broke when a source was renamed.

*Demonstrated by:* `revenue/uiowa_rfq_18649_traceability_rehearsal` (6 files). Run `python3 validate_trace.py` from that directory; observed 2026-09-19, result `trace validation: PASS`.

## Comparison

**CAP-03.** Delivery measurements are computed per service from dated records, and each figure is reported together with the measurement window and the number of records it was derived from.

*Why it matters:* Two teams' delivery figures are only comparable if both came from a stated window over a stated record count. Publishing the window next to the number is what makes a later comparison defensible.

*Demonstrated by:* `revenue/uiowa_rfq_18649_delivery_metrics` (3 files). Run `python3 -m unittest test_calculator` from that directory; observed 2026-09-19, result `Ran 6 tests in 0.006s - OK`.

**CAP-04.** Assessment output separates a completed process step from evidence that the step produced its intended result, and evidence that was never supplied stays marked unknown instead of being counted as a passing value.

*Why it matters:* A record set that is half populated otherwise reads as a clean result. Keeping unknowns visible is what stops a partial submission from being mistaken for a favourable finding, and it names the specific input still needed.

*Demonstrated by:* `revenue/uiowa_rfq_18649_recovery_evidence` (3 files). Run `python3 -m unittest test_recovery_evidence` from that directory; observed 2026-09-19, result `Ran 50 tests in 0.031s - OK`.

## Report preparation

**CAP-05.** A final report is assembled from a defined section structure that is checked against the requested scope, so a section with no supporting content is reported as empty rather than filled with generic text.

*Why it matters:* A reviewer can see which parts of the report are backed by collected material and which are still awaiting it, before the document is circulated rather than after.

*Demonstrated by:* `revenue/uiowa_rfq_18649_report_structure` (3 files). Run `python3 -m unittest test_report_structure` from that directory; observed 2026-09-19, result `Ran 55 tests in 0.147s - OK`.

## Not demonstrated

These were proposed as capabilities and are not claimed as such, because the binding below is missing. They are listed rather than removed so the omission is visible.

- **CAP-06** (evidence organization) - demonstration was not run: no executable demonstration command declared

## How to check this appendix

Run `python3 capability_appendix.py record --observed-on <date>` to re-execute every demonstration, then `python3 capability_appendix.py build`. If an artifact has changed since it was demonstrated, its claim moves itself into the Not demonstrated list.
