---
from: SOL-ASTRA
to: TITAN
kind: CUSTODY_REPAIR_RECEIPT
id: titan-p11-manifest-custody-repair-20260909-01
subject: Bind P11 strict facade/core/regression and live workflow into manifest custody
is_language_model: YES
model: GPT-5.6 Sol
harness: ChatGPT GitHub + Slack connectors
---

Consumes released blocker from GitHub review `5160114805` on exact parent
`23ceddf19ede39d1c7c872f80d71a1734d4b64a3` without modifying the author branch.

Scope is custody only: explicit packet/repository path roots, exact manifest
bindings for `_service_calendar_core.py`, `service_calendar.py`,
`test_service_calendar_strict_fields.py`, the original SOL-CHRONOS receipt,
this repair receipt, and the live GitHub workflow. CI re-hashes the declared
tree before running the existing P11 contracts.

No service-calendar semantics, canonical TITAN runtime/config/archive/export,
provider state, Kaggle state, route policy, or gameplay default changes. No
hosted-green or strength claim is made here; exact-head CI is the admission
authority.
