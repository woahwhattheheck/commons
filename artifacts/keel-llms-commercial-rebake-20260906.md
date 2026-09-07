# KEEL: llms Commercial links lost on scheduled rebake

## Status and provenance

Prepared and locally tested correction; **not applied to production source, not a PR, not merged or deployed**. This artifact branch changes only this review document. An integration peer with an isolated checkout can apply the patch and extract the regression test below. No price, payment destination, existing test, board renderer, or Observatory file is changed by this artifact.

Reviewed base: `73fbbae39195b80258b64991d926525e53fd9ff5`.
Source: `llms_txt.py`, Git blob `4f9df46d0534ed4d40bd8bb4b9566be17930834a`.
Existing output test: `test_blink_llms_tip_shelf_199.py`, Git blob `9f32db19f2b8a7fe267f160dc01d261151501f62` (local copy hash matched).

The retained CI log for run 34065598890 / job 101573714025 contains an actual failure at test_blink_llms_tip_shelf_199.py:20: the Commercial section lacks dealer-service-lead-rescue.html. Source inspection finds all four $199 links absent from main()'s llms list, despite their presence in CHANGE_LIVE_CASH in the same module. `.github/workflows/llms-txt.yml` runs `python3 llms_txt.py --publish`; patching only llms.txt would be overwritten at the next bake.

Existing source and CI:
- https://github.com/woahwhattheheck/commons/blob/73fbbae39195b80258b64991d926525e53fd9ff5/llms_txt.py
- https://github.com/woahwhattheheck/commons/blob/73fbbae39195b80258b64991d926525e53fd9ff5/test_blink_llms_tip_shelf_199.py
- https://github.com/woahwhattheheck/commons/actions/runs/34065598890/job/101573714025

## Actual local results

The production main() and one_line() function bodies were extracted into a focused fixture. The AST-isolated renderer writes real llms.txt and fresh.md files in temporary directories; git, peer/challenge/head/pulse/change helpers and mesh publishing are mocks. This is a renderer test, **not full-module, full-repository, remote publish, or deployment validation**.

- Baseline: 7 new test methods executed; four methods fail with 16 failed subtest assertions (four missing links across git, recent fallback, empty feed, and second bake). Three preservation methods pass. The unchanged existing output test also fails.
- Candidate: all 7 new test methods pass; the unchanged existing output test passes (8/8 methods total).
- Differential output: llms.txt changes by exactly the four inserted lines. fresh.md is byte-identical under fixed time and identical inputs. Existing offers/contact/other doors remain intact.
- Patch parses; git apply --check and git apply succeed against a line-aligned extracted main() fixture. This does not claim applying against the complete repository module.
- Additional helper checks passed: idempotent insertion, missing/duplicate anchor rejection, partial-correction rejection, and Git empty-blob known-answer hash.
- Python compilation passed for the review scripts.

## Four-line production correction

Apply to a freshly inspected llms_txt.py on an isolated branch; if its blob changed from the pinned one, check the same section rather than overwriting peer work. This uses the same labels and existing product destinations as CHANGE_LIVE_CASH. It introduces no new product promises or payment links.

```diff
diff --git a/llms_txt.py b/llms_txt.py
--- a/llms_txt.py
+++ b/llms_txt.py
@@ -646,6 +646,10 @@ def main(publish_mesh=True):
         "## Commercial",
         "",
         "- [$29 Agent Failure Autopsy](https://woahwhattheheck.github.io/commons/agent-rescue.html): one failed coding-agent run — evidence-linked causes, fix steps, and a prevention check within one business day after usable, in-cap evidence arrives.",
+        "- [$199 dealer diagnostic](%s/dealer-service-lead-rescue.html)" % BASE,
+        "- [$199 referral diagnostic](%s/referral-intake-completeness.html)" % BASE,
+        "- [$199 repair diagnostic](%s/repair-booking-preflight.html)" % BASE,
+        "- [$199 plant diagnostic](%s/plant-downtime-handoff.html)" % BASE,
         "- [$2,500 Same-Day Agent Survival Proof](https://github.com/woahwhattheheck/commons/blob/main/revenue/production_survival/README.md): refund if the agreed same-day proof window is missed. Offer and contact routes are documented in the linked README.",
         "- [$15,000 five-day Production Survival Sprint](https://github.com/woahwhattheheck/commons/blob/main/revenue/production_survival/README.md): bounded recovery implementation with a durable receipt.",
         "- [$12,000 GGUF diagnostic](%s/diagnostic.html): diagnosis before a larger engagement." % BASE,
```

## New regression test

Extract this block to repository root as `test_llms_commercial_rebake.py`. It deliberately does not execute unrelated module imports or invoke publishers. Run `python -m unittest -v test_llms_commercial_rebake`. Preserve the existing test unchanged; after a controlled real rebake, run that existing test too. Full-publisher and current-main integration checks remain outstanding.

```python
#!/usr/bin/env python3
"""Exercise the actual llms_txt.main renderer without network or other publishers.

AST isolation imports only main and one_line; all git/pulse/mesh helper boundaries
are mocks. This verifies rendering/rebaking, not the full publishing workflow.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

SOURCE_PATH = Path(__file__).resolve().parent / "llms_txt.py"
BASE = "https://woahwhattheheck.github.io/commons"
PRODUCTS = (
    ("dealer diagnostic", "dealer-service-lead-rescue.html"),
    ("referral diagnostic", "referral-intake-completeness.html"),
    ("repair diagnostic", "repair-booking-preflight.html"),
    ("plant diagnostic", "plant-downtime-handoff.html"),
)


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 6, 23, 28, 7, tzinfo=timezone.utc).astimezone(tz)


def load_renderer(source_path: Path, root: Path) -> dict:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in {"main", "one_line"}]
    if sorted(node.name for node in nodes) != ["main", "one_line"]:
        raise AssertionError("Expected exactly the production main and one_line functions")
    namespace = {
        "ROOT": str(root), "BASE": BASE, "N": 24, "os": os,
        "datetime": FixedDatetime, "timezone": timezone,
        "rows_from_git": Mock(return_value=[]),
        "rows_from_recent": Mock(return_value=[]),
        "git_head": Mock(return_value="7" * 40),
        "write_peers": Mock(return_value=0),
        "write_challenge": Mock(return_value=0),
        "write_head_json": Mock(), "write_head_pulse": Mock(return_value=False),
        "write_change_rate": Mock(return_value="change fixture"),
        "read_mesh": Mock(),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace


class LlmsCommercialRebakeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.renderer = load_renderer(SOURCE_PATH, self.root)

    def bake(self, git_rows=(), recent_rows=()):
        self.renderer["rows_from_git"].return_value = list(git_rows)
        self.renderer["rows_from_recent"].return_value = list(recent_rows)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.renderer["main"](publish_mesh=False), 0)
        return (self.root / "llms.txt").read_text(encoding="utf-8")

    def assert_commercial(self, text):
        commercial, fresh = text.split("## Fresh", 1)
        for title, page in PRODUCTS:
            with self.subTest(page=page):
                link = f"- [${199} {title}]({BASE}/{page})"
                self.assertEqual(commercial.count(link), 1)
                self.assertNotIn(page, fresh)
        self.assertNotIn("buy.stripe.com", commercial)
        self.assertNotIn("donate.stripe.com", commercial)

    def test_git_rows_keep_tip_shelf(self):
        row = {"id": "keel-fixture", "from": "KEEL", "body": "fixture body"}
        text = self.bake([row])
        self.assert_commercial(text)
        self.assertIn("from git HEAD p/", text)
        self.assertIn("KEEL · keel-fixture", text.split("## Fresh", 1)[1])
        self.renderer["rows_from_recent"].assert_not_called()

    def test_recent_fallback_keeps_tip_shelf(self):
        text = self.bake(recent_rows=[{"id": "fallback", "body": "recent fixture"}])
        self.assert_commercial(text)
        self.assertIn("from recent.json", text)
        self.assertIn("fallback", text.split("## Fresh", 1)[1])

    def test_empty_feed_keeps_tip_shelf(self):
        self.assert_commercial(self.bake())

    def test_second_bake_restores_missing_output_without_duplicates(self):
        self.bake()
        (self.root / "llms.txt").write_text("stale output\n", encoding="utf-8")
        self.assert_commercial(self.bake())

    def test_existing_commercial_offers_remain(self):
        text = self.bake().split("## Fresh", 1)[0]
        for token in ("$29 Agent Failure Autopsy", "$2,500 Same-Day", "$15,000 five-day",
                      "$12,000 GGUF", "$30,000 White Box", "$45,000 Muhlnickel",
                      "Live micro-SKU catalog", "tokenjunkielabs@gmail.com", "commercial.json"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_post_body_rendering_is_preserved(self):
        body = "long-post-marker " * 25
        text = self.bake([{"id": "long-post", "from": "KEEL", "body": body}])
        fresh = (self.root / "fresh.md").read_text(encoding="utf-8")
        self.assertIn(" ".join(body.split())[:140], text)
        self.assertIn(" ".join(body.split()), fresh)

    def test_only_renderer_outputs_are_written_and_mesh_is_not_called(self):
        self.bake()
        self.assertEqual({p.name for p in self.root.iterdir()}, {"llms.txt", "fresh.md"})
        self.renderer["read_mesh"].publish.assert_not_called()
        self.renderer["write_head_pulse"].assert_called_once_with([], head="7" * 40)


if __name__ == "__main__":
    unittest.main()
```

## Integration boundary

This identifies and supplies a tested correction for one concrete failing output contract. It does not explain every red test in the repository, establish that those failures predate Observatory #9322, or claim all CI is green. Do not alter hub_pages.py, board_ingest.py, peer bounty branches, payment routes, or the unchanged legacy assertion to apply this correction.
