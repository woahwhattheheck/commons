#!/usr/bin/env python3
"""One saved Commons Door exposes the integrated capability surfaces."""
from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
RESOURCES = ROOT / "resources.html"

HUMAN_LINKS = ("./commerce.html", "./orchestration.html")
MACHINE_LINKS = (
    "./revenue/outcome_commerce/manifest.json",
    "./revenue/outcome_commerce/catalog.json",
    "./orchestration/jeffersonville/frameworks.json",
    "./orchestration/jeffersonville/topology.json",
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        values = dict(attrs)
        self.links.append((values.get("href", ""), values.get("class", "")))


def links_in(path: Path) -> list[tuple[str, str]]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.links


def relative_target(source: Path, href: str) -> Path:
    parts = urlsplit(href)
    if parts.scheme or parts.netloc:
        raise AssertionError(f"expected a relative link, got {href}")
    target = (source.parent / parts.path).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError as exc:
        raise AssertionError(f"link escapes the repository: {href}") from exc
    return target


class CapabilityEntrypointTests(unittest.TestCase):
    def test_one_saved_door_has_first_class_capability_buttons(self) -> None:
        index = INDEX.read_text(encoding="utf-8")
        parsed = links_in(INDEX)
        for href in HUMAN_LINKS:
            matches = [css for candidate, css in parsed if candidate == href]
            self.assertEqual(len(matches), 1, href)
            self.assertIn("door-btn", matches[0].split(), href)

        self.assertIn(
            "This is the only link the operator should need to save or share.",
            index,
        )
        self.assertIn("crawler-access.json", index)

    def test_common_resources_composes_human_and_machine_surfaces(self) -> None:
        hrefs = {href for href, _css in links_in(RESOURCES)}
        for href in HUMAN_LINKS + MACHINE_LINKS:
            self.assertIn(href, hrefs)

    def test_new_relative_links_resolve_to_checked_in_files(self) -> None:
        for source, hrefs in (
            (INDEX, HUMAN_LINKS),
            (RESOURCES, HUMAN_LINKS + MACHINE_LINKS),
        ):
            for href in hrefs:
                target = relative_target(source, href)
                self.assertTrue(target.is_file(), f"{source.name}: {href}")

    def test_destination_pages_are_indexable_and_return_home(self) -> None:
        for href in HUMAN_LINKS:
            target = relative_target(INDEX, href)
            html = target.read_text(encoding="utf-8")
            head = html[:4096].lower()
            self.assertIn('name="robots"', head, href)
            self.assertIn("index,follow", head, href)
            destination_links = {candidate for candidate, _css in links_in(target)}
            self.assertTrue(
                destination_links.intersection({"./", "./index.html", "index.html"}),
                f"{href} has no Commons-home link",
            )

    def test_entrypoint_truth_labels_match_machine_records(self) -> None:
        resources = RESOURCES.read_text(encoding="utf-8")
        self.assertIn("does not move money", resources)
        self.assertIn("reference-only adapter and benchmark catalog", resources)
        self.assertIn("NOT_DEPLOYED", resources)
        self.assertIn("no data-center build or Rust/Go rewrite is authorized", resources)
        self.assertIn("public open doors", resources)

        frameworks = json.loads(
            relative_target(RESOURCES, MACHINE_LINKS[2]).read_text(encoding="utf-8")
        )
        topology = json.loads(
            relative_target(RESOURCES, MACHINE_LINKS[3]).read_text(encoding="utf-8")
        )
        self.assertEqual(frameworks["deployment_status"], "NOT_DEPLOYED")
        self.assertEqual(topology["deployment_status"], "NOT_DEPLOYED")

    def test_entrypoints_do_not_claim_an_a2a_agent_card(self) -> None:
        combined = INDEX.read_text(encoding="utf-8") + RESOURCES.read_text(encoding="utf-8")
        self.assertNotIn(".well-known/agent-card.json", combined)


if __name__ == "__main__":
    unittest.main()
