# ASTRA-QUARTZ TITAN runtime consumer receipt

Date: 2026-09-08

Scope: consume the already-landed ECON `FundedPaybackAdmission` and WIDEFIELD
fourth-quadrant producer through the one canonical TITAN runtime/package.

- `main.py::agent` constructs the ECON callback only when the existing
  fourth-quadrant feature is explicitly enabled.
- `TitanAgent` gives the producer/admission pair the retained terminal mechanics,
  including the exact `_parse_order` and `_refresh_prices` helpers that are not
  exposed by root mechanics.
- A runtime-only adapter translates canonical zero-quantity order placeholders
  to slot-preserving `PASS` rows for prospective evaluation and carries the
  producer's explicit physical rejoin boundary. Executed routes, WIDEFIELD's
  producer, and ECON's attributed callback remain unchanged.
- The canonical archive vendors the exact attributed ECON source; it does not
  copy or fork that implementation in the execution-lab source tree.
- `TITAN-CONFIG.json` explicitly keeps `fourth_quadrant` false. No selected
  production policy default is activated by this delivery.

Focused validation and final archive identities are recorded in the pull request
and Slack task thread after rebuilding from the publication base.

Reached day-11 probe (synthetic current-state boundary, not a full game): the
explicit opt-in scanned 24 WIDEFIELD proposals, evaluated three within its
component budget, returned a legal action in 0.567 seconds, and reported two
`incremental_purchase_not_funded` decisions plus one `incomplete_budget`.
No malformed-route result remained after the adapter. This probe does not
warrant changing the selected default or claim a strength improvement.
