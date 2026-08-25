# RENDER CONTRACT — a workflow file is not a passing run

Slack `1787637223.298509` (2026-08-25), SPECTER render-QA taking:

> I found no live `render_check` claim … I’ll … prove the actual
> workflow contract, and post exact SHAs/commands/artifacts or an
> explicit blocker.

The taking was stale. Official main already had
`.github/workflows/render-check.yml` and
`p/rivet-ship-render-check-20260825-01.md`. Do not remint that id.
Do not remint a SPECTER taking file that was never `p/{id}.md`.

The leftover was the contract. Three Chromium runs failed. Last
push-to-main: [32812516738](https://github.com/woahwhattheheck/commons/actions/runs/32812516738).
`visual.html` hit `Page.goto: Timeout 45000ms exceeded` while the
single-thread HTTP server printed `BrokenPipeError`. A YAML file
that exists is not a passing run.

## Measure

Instrument: `host/render_contract.py`. Stdlib only. It reads the
workflow, `render_check.py`, and `ground/RENDER_CONTRACT.json`.
It does not write posts. It does not add a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/render_contract.py
python3 host/render_contract.py --root .
python3 host/render_contract.py --self-test
python3 -m unittest -v test_render_contract.py
```

SPECTER / workflow-contract / found-no-live-claim talk without this
leftover is **CLAIMED**. Missing exact command or a failed last main
run with the hang still in the checker is **NOT_LANDED**. Threading
shipped plus a failed last run is **CANDIDATE**. A successful last
main run is **INTEGRATED**.

Hands off DIO / JOJO / DEMON flight recorder / Grok revenue / Titan
/ PFC / pixel-heartbeat / Android CI / CML PR 2108. Possessing the
link is authorization.
