# UIOWA-064: publish a delivery-metrics report

Run the calculator directly in a trusted checkout with Python 3.10 or newer. It uses the standard library and makes no network calls. The supplied CSV describes a fictional service, not University of Iowa performance.

From this component directory, choose an existing operator-controlled output directory and run:

```sh
python calculator.py fixtures/synthetic_deployments.csv \
  --window-start 2026-09-01T00:00:00Z \
  --window-end 2026-09-08T13:00:00Z \
  --recovery-observed-through 2026-09-08T13:00:00Z \
  --output report.json
```

This command selects five fictional deployments. Only DEP-002 has recovered by the inclusive cutoff; its observed recovery is four hours. DEP-005 remains a qualifying failure but its later recovery is excluded, so recovery coverage is PARTIAL. See [interpretation notes](64-interpretation-notes.md) for denominators, missing-classification bounds and the complete example.

Omit `--recovery-observed-through` for the retrospective mode that uses all supplied recovery records. Omit `--output` to print JSON. Use `--service` when the input includes multiple services. Deployment selection is start-inclusive and end-exclusive; all timestamps require offsets and normalize to UTC.

## Keep the evidence separate

Never choose the input CSV or an alias to it as the output. Use a new regular filename or a deliberately replaceable report; symbolic-link outputs are not accepted. Existing parent directories are required. Exit 0 indicates the report was produced. Exit 2 and an `ERROR:` diagnostic indicate an input or filesystem problem. Resolve that problem before rerunning, and do not relabel a retained previous report as a new result.

The [output contract](OUTPUT_INTEGRITY.md) explains atomic replacement and its filesystem limits. Inspect metric coverage in the resulting JSON: absent recoveries are not zero-duration recoveries, and incomplete classifications do not establish a precise full-cohort rate.

## Sources and scope

Calculator and example: Semaphore. Input/UTC and recovery eligibility: KESTREL-6D9F. Output preservation: FARADAY. Recovery cutoff and cohort interpretation: Copperfinch, integrated in #19227. This software calculates supplied records only; it does not establish source authenticity, export completeness, University findings, individual productivity, customer acceptance or release approval.
