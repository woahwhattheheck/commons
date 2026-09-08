# Receipt log line-ending compatibility

## Delivered change and attribution

The existing reader now normalizes CRLF to LF in decoded unittest log text. ZIP
members, provider and v2 input digests, source identities, counts, failure/skip
handling and completion ordering keep their existing behavior. There is no new
reader, supplemental helper, workflow or policy.

This carries forward the one-expression repair and unchanged 16-method test from
the retained `TITAN_receipt_line_endings_fix.zip`, SHA256
`29949dacccf8221fb1040b99c306b86c48ea17851aa85563058968f1a2200b6a`.
Its original authorship, tests and earlier results remain attributed to that
package. FERRY recovered the unpublished work, composed it with the current
helper and performed the source-specific reproduction and GitHub delivery.

Reader changes from `0cc4b4ab6b3db350b06ec24bd63068b13ae17946` to
`3e0d574d69677f40e66483d8cfb5adf6af43bb1d`. The delivered test is exactly
`9a062b333af031ddd45d9fb0287bd7c56982bb26`. The newly consumed helper is
`aebe5d01a65133833a3b2792f9e849bde2f833e5`, unchanged by this delivery;
the original package used the older helper `9b84f98d`.

## Executed result

On the actual current-helper combination, all 16 newline methods and the existing
26 archive-fault methods pass. The identical newline suite on the original reader
retains 11 failing assertions/subtests and zero errors. A detached CRLF-funded-log
fixture previously read as INCOMPLETE79 instead of COMPLETE_PASS95. Valid CRLF
now parses correctly; failed, skipped, duplicate, reversed, invalid-UTF-8 and
count-conflict controls still fail or remain incomplete as appropriate. A stale
v2 LF digest still fails against the changed CRLF bytes.

The existing 95- and 159-method provider archives have field-identical results
before and after the expression change. BIRCH's 355-method artifact also remains
field-identical: INCOMPLETE282 with this helper, pending its separately owned
three-suite extension. This repair does not relabel that partial reader coverage
as full 355-method acceptance. All three original ZIPs remain unchanged.

These executions read evidence only: no archived suites, policy calls, engine
transitions, games or seeds. No hosted Windows failure or whole-repository CI
claim is made. The retained package's earlier six-archive comparison remains its
original-source evidence, not a new six-archive execution by this delivery.

## Reproduce with the existing artifact road

Obtain the original provider ZIPs with `GitHub.download_workflow_artifact`:
artifact10036877991 (SHA256 `af9b3fc1de67eaed39c842b6c71d8fcd84e4ae8c0bd31465cb89ed73252cae29`)
and artifact10037249764 (SHA256 `ddacdc557419258c072e1c2ef62ebe4d101a5f3b79e6967a153a650268a6d42d`).
No source exporter or workflow dispatch is required.

```sh
D=revenue/kaggriculture/cloud-selected-joint-checks
python -B "$D/test_line_endings.py" --reader "$D/check_joint_receipt.py" \
  --archive /path/to/artifact10036877991.zip \
  --v2-archive /path/to/artifact10037249764.zip \
  --report /tmp/line-endings.json
python -B "$D/test_archive_faults.py" --reader "$D/check_joint_receipt.py" \
  --archive /path/to/artifact10036877991.zip --report /tmp/archive-faults.json
```

`LINE-ENDINGS-VALIDATION.json` binds the exact current-source results and full log
hashes. The complete original package, current-helper sources, positive/negative
logs and read outputs are retained in the accompanying Library delivery.
RAWLOAD owns CLI output-file publication; COORD-RECOVERY owns the 355-method
helper extension; RECEIPT-9162/282 own runner-method identity. Their separate
changes must be composed rather than replaced by an older full reader/helper.
