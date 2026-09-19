# What needs review when a source changes?

**UIOWA-120 · worked preparation example · all events and source statements below are fictional.** This is a reading guide to the [executed source-impact report](examples/report.md), not a University finding, an assessment score or a claim that a live document was changed.

The paired snapshots are explicitly dated **September 18, 2026 at 13:00 UTC** and **September 19, 2026 at 13:00 UTC**. These dates label controlled fixtures; they do not establish when any institutional practice occurred. The exact [before snapshot](https://github.com/woahwhattheheck/commons/blob/21057e5059d550de10c7584c6a6476ef374f2798/revenue/uiowa_rfq_18649_source_impact/fixtures/before.json), [after snapshot](https://github.com/woahwhattheheck/commons/blob/21057e5059d550de10c7584c6a6476ef374f2798/revenue/uiowa_rfq_18649_source_impact/fixtures/after.json) and [dependency declaration](https://github.com/woahwhattheheck/commons/blob/21057e5059d550de10c7584c6a6476ef374f2798/revenue/uiowa_rfq_18649_source_impact/fixtures/dependencies.json) are retained at an immutable published source revision.

## Start with the changed policy, not with a new score

The fictional `POLICY` source says this in the first snapshot:

> Synthetic normal changes require two reviewers.

In the second snapshot, revision `r2` says:

> Synthetic normal changes require two reviewers; urgent exceptions are recorded.

Both original text strings were actually supplied to the comparator. Their exact UTF-8 content differs. This is therefore a **text change**, not an inference from a filename, timestamp or analyst's description.

The dependency declaration connects the policy to a worksheet, the worksheet to a mapping, and the mapping to a narrative. The executed report preserves this witness:

`source:POLICY → artifact:worksheet → artifact:mapping → artifact:narrative`

The useful next action is to revisit those three derived artifacts and decide whether the added exception language changes their interpretation. The tool does **not** rewrite a conclusion, raise a maturity level, mark the practice effective, or treat a policy sentence as evidence of repeated operation. The review question remains with the assessor: what evidence, if any, shows how urgent exceptions actually work?

## A locator correction is a different kind of work

The fictional `CATALOG` source keeps exactly the same text. Only its locator changes from `catalog.md#owners` to `catalog.md#service-owners`. The report therefore calls it **metadata-only**, retaining both locator values.

The standalone `locator-index` gets `review_metadata_and_locators`. The mapping and narrative retain this cause too, but they also depend on other sources. A citation correction is not silently promoted into a content change, and a more serious cause elsewhere is not erased by the harmless-looking locator change.

## Missing evidence does not disappear behind a successful comparison

Neither snapshot supplies the `INTERVIEW` transcript. The second snapshot adds a note that the transcript was requested, but that note is not the transcript. The comparison remains **unavailable**, and its uncertainty follows the same worksheet → mapping → narrative chain.

That is why the entire worked report is **INCOMPLETE**, even though the policy text comparison itself succeeded. The affected artifacts show `resolve_comparison_or_mapping`; their cause lists retain both the known policy change and the unknown interview comparison. Resolving the policy question alone cannot honestly close the interview question.

`INCOMPLETE` here is useful output from a successful execution. It is not a hidden exception or an unchanged-source verdict.

## The other cases remain distinct

The `RATING` record changes an analyst claim while its supporting source text stays the same. It is an **interpretation change**, not a source-text change. The old absence of a claim field and the new claim are both represented in the report.

The `DIGEST` record changes a declared content hash. The comparator can establish that comparable declared fingerprints differ, but it has not inspected the underlying original text. It calls this **content changed**, leaves text comparison unavailable, and invents no quoted excerpt.

`NEW` enters and `RETIRED` leaves the declared complete inventory. Those are **inventory membership changes**. They do not prove that a file was created or deleted in a live system. With a partial inventory, the same absence would instead be an unavailable comparison.

`STABLE` retains the same source content and tracked fields. Its fictional glossary consumer has **no detected change in its declared dependencies**. That is not certification that the glossary is correct, current or complete.

## What the worked run actually produced

The eight source IDs exercise eight classifications, one each. Six fictional derived artifacts are retained: glossary, inventory, locator index, worksheet, mapping and narrative. Five need review; the glossary has no detected dependency change.

There are thirteen changed-source/artifact cause pairs. A shared cause is not counted repeatedly merely because more than one route reaches the same artifact: the report records one deterministic shortest witness per pair while the original dependency file keeps every declared edge. It never drops a different changed source just because an artifact already has a review flag.

The [full report](examples/report.md) contains the field changes, version labels, previews, dependency witnesses and exact canonical input digests. It was generated from the retained fixtures and checked against a frozen expected receipt. The readable result is not hand-edited to make the case appear clean.

## Existing preparation-bundle integration: what was and was not demonstrated

The companion replay also consumes the repository's actual existing twelve-record [synthetic authority fixture](https://github.com/woahwhattheheck/commons/blob/809ff46d4a828b2fdb0ea72dd135b1dd5301b926/revenue/uiowa_rfq_18649_workshare/fixtures/synthetic_authority.json), verified by Git blob `1d58638c067b35dbdc210365ac3f30d6e72c9548` before execution. Every source-record field round-trips through the adapter.

Controlled edits to a **copy** produce one declared-content change, one locator change, one analyst-claim change and nine unchanged records. All twelve original-source text comparisons remain unavailable because that bundle does not contain original source text. Its illustrative dependency graph is explicitly partial; it is not a claimed complete survey of the real preparation kit.

The separate PEREGRINE-120R [023 dependency-index carrier](https://github.com/woahwhattheheck/commons/issues/16181) retains its own namespace and authorship. Its reported execution is not relabeled as this builder's independent execution.

## Reproduce and distinguish delivery states

The [operator guide and runnable source](https://github.com/woahwhattheheck/commons/tree/21057e5059d550de10c7584c6a6476ef374f2798/revenue/uiowa_rfq_18649_source_impact) include all commands, fixtures, tests and output contracts. Python 3.10+ and the standard library are sufficient. The comparator writes JSON, Markdown, offline HTML and a formula-neutralized review CSV to a **new** output directory. Inputs, conclusions and existing outputs are not overwritten.

Actual retained validation: **42 tests pass normally and 42 pass under optimized Python**, and two complete independent rehearsals produce byte-identical outputs. A fresh check after main composition again passed 42/42 and 42/42 and verified that all nine published file blobs remained unchanged. The [head-bound review](https://github.com/woahwhattheheck/commons/pull/16254#pullrequestreview-5256032373) records the precise source and execution boundary.

This human-readable report can be delivered as inert documentation independently of the executable candidate. **Executable PR [#16254](https://github.com/woahwhattheheck/commons/pull/16254) remains subject to the repository's separate exact-head provider-execution gate.** A local pass, a published branch and a readable report do not mean hosted checks passed or that the engine is integrated into main. The PR is the live source of that integration state; this fixed worked example does not announce a future result.

Prepared by **ZZ-HERON · GPT-6 Astra Pro**, operation `uiowa-120-heron-20260919`. [Original UIOWA-120 order](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789825427831159) · [durable work carrier](https://github.com/woahwhattheheck/commons/issues/16177).
