# UIOWA-064 report publication

Output-preservation behavior comes from FARADAY's repair, composed with the existing calculator and input/UTC handling. It is independent of the metric arithmetic.

The CLI checks the destination, writes the complete UTF-8 report to a temporary file in that directory, flushes and synchronizes it, rechecks source/destination identities, then replaces the destination. A failed write, flush, encoding or replacement does not publish a partial new report. A previous report remains the previous generation until replacement succeeds.

An existing ordinary report may be deliberately replaced. The input CSV and its hardlink aliases cannot be used as output. Symbolic-link outputs, including dangling links, and nonregular destinations are refused. A hardlink to an unrelated report is replaced only at the selected name. A symlinked parent can be used in an operator-controlled directory, but aliases to the input remain refused.

The destination's parent directory must already exist. Replacement uses the temporary file's metadata, not the previous file's permissions or ACLs. This is complete-file replacement for operator-controlled directories, not power-loss durability, hostile directory-swap protection, or concurrent-writer serialization. Parent-directory synchronization is not performed.

Use [the operator guide](OPERATOR_OUTPUT_REHEARSAL.md) to run the calculator directly. Source evidence, customer acceptance and export completeness are not established by a successful output write.
