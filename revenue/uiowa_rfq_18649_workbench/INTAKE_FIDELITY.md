# Original-evidence intake fidelity

This is the candidate/authority upload path in the existing RFQ 18649 analyst
workbench. It is separate from saved-draft restoration, report verification,
review reconciliation, assessment scoring, and permission to deliver findings.
The examples below are synthetic parser examples, not University evidence.

## Operator contract

Choose one UTF-8 candidate JSON object and one UTF-8 authority JSON object. Each
file must be no larger than 1 MiB. The complete request, including its existing
`candidate`/`authority` envelope and original whitespace, must fit within 2 MiB.
A byte-order mark is rejected as JSON syntax rather than removed silently.

The browser checks complete-object syntax and transmits each original JSON text
segment without parsing and reserializing its values. Whitespace, escape spelling,
member order, numeric spelling, and duplicate members therefore reach the server
unchanged. HTTP framing and the surrounding envelope are not the original file;
this is not a claim of a whole-file transport digest or source authenticity.

The server rejects duplicate object members, including escaped-equivalent names
and duplicates inside nested arrays. Repetition in separate objects is valid.
Invalid UTF-8 and lone-surrogate strings/keys receive a controlled diagnostic
before the compiler adapter runs. Valid supplementary Unicode and genuine U+FFFD
characters remain valid data.

Large integer literals retain Python's integer semantics rather than passing
through JavaScript binary64. Python's configured integer-digit limit still applies.
Finite decimal/exponent literals keep the compiler's existing Python `float`
interface: **this does not supply arbitrary-precision decimal arithmetic**.
Non-finite constants, floating overflow, and nonzero floating underflow are rejected
instead of becoming null, infinity, or zero. Actual zero, including zero with a
large exponent, remains zero. Small representable nonzero floats remain nonzero.

A replacement attempt still clears the preceding report, draft notes and export
controls immediately. A failed replacement does not leave a stale export active.
Reset or a newer demonstration/report generation still defeats a late read or
inspection response. This change does not reinterpret compiler reports, alter
source identifiers or report receipts, restore drafts differently, or create
assessment/commercial authority.

## Reproducible synthetic observations

At the retained pre-repair UI composition `c4c305db7944cb305625836d4767d6abcc37ae36`,
executing the actual application on this candidate:

```json
{"count":9007199254740993,"ratio":0.123456789012345678901,"tiny":1e-400,"large":1e400,"duplicate":1,"duplicate":2}
```

produced this request fragment before HTTP/compiler intake:

```json
{"count":9007199254740992,"ratio":0.12345678901234568,"tiny":0,"large":null,"duplicate":2}
```

The repaired path transmits the original fragment. The server then rejects its
duplicate/unsupported numeric content rather than accepting transformed evidence.
A separate valid integer-only example reaches the recording adapter as
`9007199254740993`, not `9007199254740992`. The original fragment is intentionally
not a complete compiler candidate and is not used to assert an assessment result.

## Executed test boundary

From this directory:

```sh
python -m unittest -v test_intake_transport.py
python -O -m unittest -v test_intake_transport.py
python -W error::ResourceWarning -m unittest -v test_intake_transport.py
```

The existing root test battery discovers the same tests through
`test_uiowa_intake_fidelity.py`. Node.js with standard `fetch`, `Blob`,
`TextEncoder` and `TextDecoder` is required. Missing Node is an error, not a skip.
The suite runs the actual `app.js` in an explicitly small DOM adapter and sends
actual HTTP requests to the actual `server.py` on an ephemeral loopback port.
Its compiler adapter is a recording spy and its report is labeled synthetic.
This proves intake and replacement behavior, **not Chromium/layout, full parent
compiler execution, source authenticity, or live-provider integration authority**.
The existing real-compiler/browser suites remain separate integration checks.

The predecessor control uses the same tests with an explicit source directory:

```sh
UIOWA_INTAKE_SOURCE=/path/to/original-workbench \
  python -m unittest -v test_intake_transport.py
```

All decoder-resource exception injection is labeled in the test. The suite does
not infer a universal nesting limit from one Python build. The recorded predecessor
failure count includes subtests and formatting-preservation assertions; it is not
a count of independent product defects.

## Provenance

Original UI composition: ZZ–Keystone-43CF and ZZ–Trellis, retained PR #16145.
Original-evidence transport repair and execution: ZZ-KESTREL-47 / GPT-6 Astra Pro,
operation `uiowa-original-intake-kestrel47-20260919`. Existing saved-draft behavior
and original authorship are retained. `INTAKE_EXECUTION.json` binds the executed
source/test bytes and distinguishes local conformance from pending integrations.
