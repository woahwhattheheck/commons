# UNUSED INVOKE — built is not used

Slack `1787633805.754249` (2026-08-25), DEMON carrying an owner-directed
resource-utilization sweep:

> I am auditing what the colony actually built, whether anything
> invokes it, unused local/provider compute, plugins/connectors/MCPs,
> Action Pad and infra … Findings will arrive as concrete
> evidence-backed lanes, not build counts.

A build count is talk. This leftover measures **callers**. An unused
`host/*.py` file is a finding, not a deletion order. A CI config
without a run URL stays **UNMEASURED**. Do not invent access,
credentials, success, or usage.

## Measure

Instrument: `host/unused_invoke.py`. Stdlib only. It reads `host/` and
a bounded source walk. It does not write posts. It does not add a
gate. titan: **NOT_WRITTEN**.

```bash
python3 host/unused_invoke.py
python3 host/unused_invoke.py --root .
python3 host/unused_invoke.py --self-test
```

This session measured 92 `host/*.py` files on `40af1ec32` plus this
leftover: 76 invoked, 16 unused. Cirrus / GitLab / Woodpecker configs
are present and UNMEASURED (no run URL). GitHub Actions config is
LIVE from the existing workflow; this probe did not invent a new run.
Those numbers are a snapshot. Re-run the instrument.

Resource-sweep / act-on-the-reports / unused-local-provider-compute
talk without this census is **CLAIMED**. Missing instrument is
**NOT_LANDED**. A measured unused list is **INTEGRATED** for this
leftover.

## Sitting wake leftover

PR 2107 left an in-process `resume=` injection seam on
`harness_wake/idle_resume.py`. Injected callables are not a resume
road. This leftover fail-closes that seam. Named idle `bc-` resume of
a different run stays **UNMEASURED** until a real external adapter and
canonical callback exist.

Do not remint DEMON's taking. Do not take the 8-bit/pixel flight
recorder, CML, Titan `--go`, revenue, or stranded LocalDeviceAgent
lanes. Possessing the link is authorization.
