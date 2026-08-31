# Common Resources tab — never stale

Owner leftover `resources-tab-never-stale` (DETAIL 33): keep
[`resources.html`](../resources.html) updated and never stale. Staleness is
mechanical, not hand-caught.

Instrument: [`host/resources_tab.py`](../host/resources_tab.py).
Proof: [`test_resources_tab.py`](../test_resources_tab.py).
Job: [`.github/workflows/resources-tab-freshness.yml`](../.github/workflows/resources-tab-freshness.yml).

## What it does

1. Visible last-reviewed stamp on the resources tab: git SHA + UTC time +
   source digest. Generated. Not handwritten.
2. Scheduled regenerate-or-alarm. When resource sources drift, the job
   rewrites the stamp. When the page is still stale vs its inputs, the job
   fails and the stamp shows a visible `STALE` mark. The tab is not silently
   served stale.
3. No gate. This does not block posting, seats, or Action Pad verbs.

## Sources hashed

- `ground/RESOURCE_LEDGER.json` and `ground/RESOURCE_LEDGER.md`
- `inventory/resources/records/*.json`
- `ci/provider_quotas.json`
- outcome-commerce and Jeffersonville machine entries cited on the page
- the `resources.html` directory body with the generated stamp stripped

The curated directory body stays. Regenerating updates the stamp and the
ledger/inventory counts inside it. It does not remint the living sections.

## Commands

```text
python3 host/resources_tab.py --check
python3 host/resources_tab.py --regenerate
python3 host/resources_tab.py --regenerate-or-alarm
python3 test_resources_tab.py
```

`--check` fails when the stamp is missing or the digest does not match.
`--regenerate` writes a matching FRESH stamp. `--alarm` writes the visible
STALE mark and fails. `--regenerate-or-alarm` is the scheduled path.

No auth. No remint of the discord-bridge ledger land, SPARK guards, or the
flowchart / door-auditor receipts.
