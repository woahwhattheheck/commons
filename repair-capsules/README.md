# Repair Capsules: local evidence workbench

Open `index.html` and use the page. No build, package installation, backend,
account, upload, or command execution is part of the application. Keep
`capsule.js` beside the HTML. A modern browser with Web Crypto is required for
SHA-256 export; localhost or HTTPS can be used when local-file Web Crypto is
unavailable.

## First useful loop

1. Choose **Try Commons demo** or **Try command demo**, or enter your own title,
   environment fingerprint, broken state, logs, and next repair action.
2. Check the known-good box only when a baseline is actually known. An unchecked
   baseline is `null`; a checked, empty baseline is deliberately empty text.
3. Add exact private values, one per line, for sensitive data the heuristic
   patterns would not recognize. Choose **Preview redacted evidence** and review
   the exact export preview, including the environment and intervention history.
4. **Export capsule** saves a portable JSON file. **Open capsule** reopens it,
   checks its checksum, redacts supported fields again, and displays the delta
   and next action without any hidden incident history.
5. Record what you actually tried and its observed result. Export again to carry
   that updated history to another person or agent. No action text is executed.

Both built-in examples are explicitly **synthetic demonstrations**, not evidence
of a real Commons or customer incident. They exercise a stale static-page
revision and a report command pointing at a missing input file. Imported
provenance, timestamps, actions, and results are assertions supplied by the
capsule author, not independently verified facts.

## Privacy and integrity: measured limits

All processing happens in the page. There is no automatic browser storage,
network request for capsule contents, analytics, environment dump, or upload
endpoint. The page's CSP disables outbound connections. User-entered raw text
remains in the form until it is replaced, the workspace is cleared, or the page
is closed. Export is the persistence mechanism; browser extensions and browser
session recovery are outside the application's control.

Redaction covers common secret assignments, bearer/basic authorization, cookie
headers, common provider token patterns, URL credentials, private-key blocks,
email addresses, home-directory identities, and supplied private literals. This
is **heuristic, not a privacy guarantee**. Unknown formats, nested structured
secrets, encoded secrets, and other personal data may be missed. Inspect the
complete export and use private literals for additional sensitive values.
Redaction counts describe replacement passes, not a count of distinct secrets.
Only supported capsule fields are reopened; unknown extension fields are not
preserved. Diffs compare the redacted states: two different secrets can become
the same mask, so equal masked text does not prove the original states matched.

The SHA-256 value is an **unkeyed checksum**, not a signature, identity check,
authentication mechanism, or approval. Anyone who changes the payload can also
recompute it. Import shows `MATCH`, `MISMATCH`, or `MISSING`; a mismatch or absent
checksum does not prevent inspection. Export computes a new checksum over the
current redacted payload. The UI separately retains the imported checksum status.

Text fields support 128 Ki UTF-16 code units each, up to 100 intervention entries,
and a 2 MiB UTF-8 serialized capsule. Large state differences use an explicitly
labeled replacement view rather than quadratic diff work. The UI shows up to
300 diff lines; full redacted states remain in the export. No arbitrary file
extraction or command replay is implemented in this first slice.

## Run checks

From the repository root, with Node.js 20+:

```sh
node --test repair-capsules/test.cjs
```

Optional real-browser smoke test (requires the Python Playwright package and a
Chromium browser):

```sh
python repair-capsules/browser_smoke.py
# Optional system browser and screenshot output:
CHROMIUM_PATH=/usr/bin/chromium SMOKE_ARTIFACT_DIR=/tmp/rc-proof \
  python repair-capsules/browser_smoke.py
```

The browser test covers page load, both demos, export/import, intervention
history, checksum mismatch, inert HTML, literal redaction, baseline semantics,
mobile overflow, lack of external requests/storage, and direct local-file use.
It serves this folder on an ephemeral loopback port and shuts down on completion.

### RIVET execution record — 2026-09-04

`node --test repair-capsules/test.cjs`: **33 passed, 0 failed** in the ChatGPT
cloud container (Node 22.16.0). HTML inline-script syntax and core JavaScript
syntax also passed. Browser execution was attempted, **not passed**:
`agent-browser` was absent; Playwright's bundled Chromium was absent; the
available `/usr/bin/chromium` returned `net::ERR_BLOCKED_BY_ADMINISTRATOR` for
both loopback HTTP and `file://` navigation. No browser policies were changed.
The full browser smoke is provided for execution in a normal browser environment;
no end-to-end browser acceptance or under-two-minute independent-user result
is claimed from this environment.

A separate **in-memory DOM/render check passed** using actual page code with a
Node-sealed synthetic capsule. It found and fixed a checksum wrapping defect:
390px viewport width originally produced a 601px document; after the CSS repair,
document width is 390px. Desktop render, visible diff/next action, inert HTML,
and workspace clearing also passed with no script errors. This allowed-mode
check does not navigate URLs, modify browser policies, or prove browser Web
Crypto, downloads, imports, or hosted behavior. Reproduce it with:

```sh
python repair-capsules/render_smoke.py
```

Scope: only `repair-capsules/`; no shared runtime, policy, authentication, OneTake,
or C1 transport modifications. RIVET claim is in the Repair Capsules kickoff
thread in Slack #coordination (`1788558472.004109`).
