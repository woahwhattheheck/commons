# Native UIOWA-039 bridge

This extends the retained UIOWA-124 carrier #16188. No review-cycle or compiler source is modified. The bridge uses the now-published contract from ZZ-ORRERY-K47's UIOWA-039/094 source: `review.py` blob `9bf19ae0c022c936e0591a171fa4496f1cb6b282`, `parent_adapter.py` blob `269ed1386917b88cdce79ae4f9c2531d73662176`, branch `swarm-zz/uiowa-039-094-orrery-k47-review`. This supersedes the README's first-publication note that the source was unavailable.

## Preparation and actual native application

```sh
cd revenue/uiowa_rfq_18649_review_import
python -m unittest -v test_comment_import.py test_native_bridge.py
python -O -m unittest -v test_comment_import.py test_native_bridge.py
python native_bridge.py comments.csv original-draft.json original-report.json \
  --source-id review-round-one --cycle-id REVIEW-ROUND-ONE \
  --new-version DRAFT-2 --out /tmp/uiowa124-preparation
```

Add `--apply-open` to apply the imported OPEN comments through the actual native `build_bundle`, then independently call native `verify_bundle` on the written result. Native parent inspection verification and document validation happen before any output is written. The compiler report is unchanged; no finding, recommendation, evidence, approval, or proposed change is inferred from CSV columns. Native input restrictions are reported, never bypassed or silently normalized.

A complete repository checkout with the native review-cycle and workshare compiler is required for these commands. The bridge creates a new directory and never overwrites an original draft. If no new native comment is available, `--apply-open` creates no empty draft revision. Exit 1 means a written preparation/application still contains unresolved source/native inputs; the full records remain in `preparation.json` alongside every successful mapping. Exit 2 is a structural/dependency/application error.

## Source fields versus native fields

Catalog entries are derived from exact native finding IDs, document version and source index; they carry the native document digest. The native canonical digest includes a final LF, unlike the staging-core digest; this difference is implemented and unit-tested explicitly. Stable native comment IDs are `IMP-` plus the SHA-256 of the logical `(source_id, comment_id)` pair. Unusual source IDs remain untouched in the sidecar instead of being mangled into native identifiers.

`comment_kind` must be one of native `factual`, `evidence`, `wording`, `interpretation`, `priority`; missing/unknown kinds remain unresolved. Original text is passed verbatim to native `comment`. Reviewer roles survive in `mapped[].reviewer_role` and the complete source values. They do not automatically become disposition owners: `owner_role` is `UNASSIGNED` unless explicitly supplied. Source `decision`, `supplied_decision`, `proposed_edit`, and arbitrary extra columns stay in provenance; native `decision` is always `OPEN`, and `proposed_changes`/`source_ids` are empty until actual downstream review.

Same-ID pending native comments with matching target/text are reported `ALREADY_IN_REVIEW`; different text becomes `NATIVE_ID_CONFLICT`. Reapplying an already recorded cycle ID is rejected by native history. Keep each application receipt and use stable cycle IDs; creating a new cycle ID intentionally begins a different review operation. Changed source variants remain unresolved in core state rather than overwriting an earlier import.

At the source version above, native `text()` rejects CR characters, including embedded CRLF. The bridge preserves the original and reports `NATIVE_TEXT_REJECTED`. Upstream compatibility request is on #16139 comment5742526634; there is no hidden LF conversion. The actual native rehearsal uses quoted multiline LF comments and CRLF CSV record terminators.

## Full real-parent rehearsal — not a stub

```sh
python native_rehearsal.py --out /tmp/uiowa124-native-normal
python -O native_rehearsal.py --out /tmp/uiowa124-native-optimized
```

This compiles the existing `synthetic_packet.json` and `synthetic_authority.json` with the real parent compiler, validates the real report, builds a native synthetic draft, imports five source rows, then exercises actual native application, rendering and regeneration. Expected preparation: two OPEN comments, two unresolved references, one duplicate source occurrence. A separate, explicitly labelled synthetic disposition fixture accepts one title edit and retains one interpretive disagreement. Neither that fixture nor a supplied CSV decision is used to infer real acceptance. The generated native response bundle must preserve original comment text, retain one unresolved disagreement, keep source/compiler states unchanged, and regenerate byte-for-byte.

The output includes full preparation/provenance, the explicit synthetic review fixture, the native original/revised/response bundle, and a receipt binding actual parent source files and output digests. Any missing real dependency fails nonzero; nothing is silently skipped. `test_native_bridge.py` tests schema preparation with deliberately minimal native-shape objects and an explicit text-rejection callback, not parent integrity. Executed local scope at publication: 48/48 unit/CLI/adapter tests normally and under `-O`; compilation passed. Full-parent execution must be recorded separately before representing the end-to-end path as verified.
