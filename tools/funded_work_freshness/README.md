# Funded-work freshness fence

Read-only intake gate for paid-work candidates before they enter a revenue/work feed.

The core deliberately does **no network, claim, comment, payment, sponsor contact, security testing, or provider mutation**. Callers inject an existing web/GitHub reader and provide the candidate URL plus the advertised amount, currency, platform, and source timestamp. The reader returns independently observed canonical state, occupancy signals, activity, payment-mechanism presence, acceptance-criteria reachability, and security-bounty classification.

`validate_candidate()` emits an immutable, deterministic receipt with four statuses:

- `actionable`: canonical target is open, unoccupied, recent, funded, and acceptance criteria remain reachable;
- `occupied`: canonical target is open but an assignee, visible claim, or active competing PR exists;
- `stale`: canonical target is closed/missing, or the funding/acceptance path is explicitly gone;
- `ambiguous`: an authority check is unresolved, activity is too old, or the item is security-sensitive.

Security bounties always route `research_only`. Unknown authority never becomes `actionable`.

## Minimal API

```python
from tools.funded_work_freshness.validator import Candidate, validate_candidate

receipt = validate_candidate(
    Candidate(
        candidate_url="https://board.example/bounty/123",
        advertised_amount="1000",
        currency="USD",
        platform="ExampleBoard",
        source_timestamp="2026-09-13T06:20:00Z",
    ),
    existing_reader,
)
print(receipt.to_json())
```

The SHA-256 binds the normalized candidate, independent observation, individual checks, classification, route, and check timestamp. Recompute it with `verify_receipt()` before consuming a stored receipt.

## Tests

Run from this directory:

```bash
python -m unittest -v test_validator.py
python -O -m unittest -v test_validator.py
python -m py_compile validator.py test_validator.py
```

Fixtures include both stale Omi board-listing mismatch examples requested by the build order, one truly open candidate, occupancy, unresolved authority, old activity, security routing, receipt tamper detection, and fail-before-reader input validation. All external evidence is injected; tests perform zero network calls.
