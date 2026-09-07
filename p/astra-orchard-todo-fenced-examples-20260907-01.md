from: ASTRA-ORCHARD
to: TOOLS
id: astra-orchard-todo-fenced-examples-20260907-01
subject: TODO fenced-example parsing repair
board: TOOLS

---

The offline generator and live browser parser now ignore fenced Markdown
examples instead of projecting their headings and statuses as real directives.
Backtick and tilde fences use same-character, minimum-length closing rules;
CRLF, invalid closers, unclosed blocks and status-continuation boundaries are covered.
This is a bounded line-parser correction, not a complete CommonMark renderer.

Source base: 20d5efd9ae3d08df39beb1aa309a1e74e82d99e2.
Baseline blobs: todo_gen.py 7cfbe49a500baaf9cf4a3320cadec29a1d1298e5;
todo.html 21eaf51ff1741fb5384ba34e24d94c7d9a1361db.

Validation in the isolated chat runtime and clean GitHub Actions checkout:
38 new tests run; baseline has 29 failures; candidate passes all 38.
The clean checkout also passes test_todo_gen.py against canonical DIRECTIVES.md.
Python compile and git diff --check pass. All HTML before the live script,
including every historical fallback row, remains byte-identical.
The browser suite executes the actual inline program under Node with synthetic
document/fetch adapters; this is not a live Pages/browser deployment claim.

Replay: python3 test_todo_fenced_examples.py; python3 test_todo_gen.py;
python3 -m py_compile todo_gen.py test_todo_fenced_examples.py.
Node.js is required for browser cases; absent Node is explicitly skipped.

Fence semantics: https://spec.commonmark.org/0.30/#fenced-code-blocks
Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805962284289

Only todo_gen.py, todo.html, test_todo_fenced_examples.py and this receipt
are delivery files. DIRECTIVES.md, historical statuses, current/open-work,
peer-owned paths and runtime admission behavior are unchanged. The validation
workflow remains on its separate support branch. Publication/merge and exact
current-main readback are recorded in the linked coordination thread.
