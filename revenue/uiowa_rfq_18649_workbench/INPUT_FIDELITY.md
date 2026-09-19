# Original-input fidelity at the workbench boundary

Seat: ZZ-KESTREL-RAW17 (GPT-6 Astra Pro). Operation: `uiowa-workbench-input-fidelity-kestrel-raw17-20260919`.

## Why this changes the real operator workflow

The previous import handler decoded each file with `Blob.text()`, parsed it with `JSON.parse`, then sent `JSON.stringify({candidate, authority})`. That normalization removed duplicate object members before the server's existing duplicate-key validator saw them, rounded integers outside JavaScript's safe range, and replaced malformed UTF-8. Two individually permitted 1 MiB files could also exceed the unchanged 2 MiB HTTP cap once the envelope was added.

The repair is confined to `app.js`. The actual import handler reads the original bytes, decodes UTF-8 with `fatal: true`, validates that each document is one complete JSON object, and inserts the original validated text into the existing `candidate`/`authority` envelope. The parsed JavaScript object is never used as transport data. The complete envelope is measured in UTF-8 bytes before the request is made. A byte-order mark is retained during decoding and rejected by JSON validation, not silently stripped.

The parser remains the existing server/parent compiler. Duplicate keys are deliberately preserved on the wire so its existing validator rejects them. There is no second evidence model, new endpoint, schema change, authority input, HTML/CSS change, or server configuration change. Existing same-origin, loopback, no-store and failed-replacement behavior remains in force.

## Executed evidence

The source reconstruction was verified against Git blob hashes before testing:

- Original `app.js`: `f180d24e5bb05489774d8c0baa4f60d3fd978656` (10,008 bytes).
- Unchanged `server.py`: `42ab51cd91e2c196909c69c4f056a2552c158001` (10,524 bytes).
- Repaired `app.js`: `37bdcef9eae703d3a82cb6daf6e521d2cb8999a6` (11,522 bytes).

`test_input_transport.js` executes the complete actual `app.js` file and its registered import-click handler in Node, with controlled DOM and response doubles. It does not reproduce a substitute import function. Its `--bridge` mode emits the actual request bytes for the Python HTTP tests.

`test_input_transport.py` replays those bytes into the actual loopback server, with a recording adapter that observes the arguments supplied at the compiler boundary. It checks duplicate rejection before adapter invocation, integer preservation, exact document fragments, UTF-8 handling, envelope bounds, unchanged origin rejection, and refusal of an added trusted-root input. All test input is synthetic.

Observed in the isolated checkout:

| Execution | Result |
| --- | --- |
| Original app against the new Node suite (negative control) | 16 passed, 14 failed |
| Repaired actual app, Node suite | 30 passed, 0 failed |
| Actual loopback HTTP transport cases | 14 passed, 0 failed |
| Additional real-parent compiler/receipt test | 1 explicit skip: parent checkout absent |
| Root discovery wrapper, normal Python | 2 passed |
| Root discovery wrapper, optimized Python | 2 passed; 30 Node and 14 HTTP cases passed; same explicit parent skip |
| Root discovery with ResourceWarning treated as error | Passed; same explicit parent skip |

The negative control fails on original document spelling, large integers, numeric spelling, four duplicate-key cases, string escaping/key order, three malformed UTF-8 cases, BOM stripping, an incorrect file-size declaration and combined-envelope overflow. It is not a suite that simply blesses either implementation.

An initial Python Unicode fixture accidentally used a JavaScript-style surrogate-pair escape. That fixture failed before transport execution and was corrected to a valid Python Unicode scalar. It was a test-fixture mistake, not an application defect.

## Re-run

From the repository root, with Node.js available:

```sh
python3 -m unittest -v test_uiowa_workbench_input_transport.py
python3 -O -m unittest -v test_uiowa_workbench_input_transport.py
node --check revenue/uiowa_rfq_18649_workbench/app.js
node --check revenue/uiowa_rfq_18649_workbench/test_input_transport.js
```

For a required-parent integration run in a full checkout:

```sh
test -d revenue/uiowa_rfq_18649_workshare
python3 -m unittest -v test_uiowa_workbench_input_transport.py
```

The additional test compares the full HTTP-returned report with direct inspection of the same synthetic parent fixtures, including the receipt and untrusted mode. A missing parent is explicitly skipped in isolated transport checkouts; it must not be described as a passing compiler run. Missing Node is an error, not a silent skip.

The negative control can be repeated without changing the tracked app:

```sh
git show <pre-repair-commit>:revenue/uiowa_rfq_18649_workbench/app.js > /tmp/workbench-before.js
WORKBENCH_APP=/tmp/workbench-before.js node revenue/uiowa_rfq_18649_workbench/test_input_transport.js
```

## Composition with the retained restore/Markdown work

Keystone's #16145 consolidates the earlier Trellis #16130 work. Keep its handoff, Markdown and generation/revision logic; do not replace that UI wholesale with an older copy. The transport delta consists of `validateJsonObjectText`, the byte-preserving `readJsonFile`, `buildInspectionBody`, and changing the inspection request body to `buildInspectionBody(candidate, authority)`.

`readJsonFile` now returns original JSON source text, not a parsed object. Saved-draft restoration must retain its separate strict parser/schema validation; do not feed raw text to code expecting an already parsed draft. File doubles in adjacent tests must implement `arrayBuffer()` and VM environments must expose `TextDecoder`/`TextEncoder`, as real browser File and global objects do. Re-run adjacent application and rendered-browser tests after composition.

Coordination and execution receipts: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789826290475859

## Limits

These executed checks establish the original-input transport and HTTP parser boundary. They do not establish visual quality, accessibility, a rendered-browser pass, hosted CI completion, or a full parent-compiler pass in the isolated checkout. The change does not provide arbitrary-precision JSON semantics throughout reports: the unchanged Python compiler still owns numeric validation and representation after parsing. It does not change escaped-surrogate handling, compiler scoring, signatures, report receipts, or any approval/payment authority. No customer evidence, external call, submission, scheduling or paid execution is involved.
