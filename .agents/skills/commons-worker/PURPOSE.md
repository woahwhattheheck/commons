# Commons worker outcome capture

Commons improves across workloads when new execution outcomes survive the job
that produced them. The existing experience compiler already distinguishes raw
evidence, compiled knowledge and active skills; this dispatcher now routes new
transferable outcomes into that existing process after the assigned work.

Motivating compiled patterns:

- [Generated output and its source](../../../experience/wiki/patterns/change-generator-with-generated-output.md)
  retains the failed rebuild and the landed repair from PR 11950.
- [Shared operation identity](../../../experience/wiki/patterns/share-operation-identity-across-carriers.md)
  preserves the command-center mechanism from the PR 9987 activation receipt.

The procedure excludes duplicate receipts and keeps runtime context compact.
Compiler and retrieval tests exercise growing evidence, retained failures,
source links and cross-workload selection. These checks do not establish a
model performance gain from the instruction change.
