from __future__ import annotations

import unittest

from host import agent_control_surface as surface


class EmptyText:
    def __str__(self) -> str:
        return ""


class AgentControlEmptySummaryTests(unittest.TestCase):
    def fixtures(self) -> tuple[dict, dict, list, dict]:
        return (
            {
                "schema": "commons-agent-discovery/v1",
                "contact_methods": [
                    {"type": "action-pad", "url": "https://example.test/action", "preferred": True},
                ],
                "continuity": {"pulse": "pulse.json", "recent": "recent.json"},
            },
            {"seq": 42, "head": "a" * 40, "ts": "2026-08-29T00:00:00Z"},
            [],
            {
                "schema": "commons-resource-ledger/v2",
                "snapshot": {"observed_at": "now"},
                "surfaces": [
                    {
                        "name": "swarm",
                        "kind": "AGENT_ROUTER",
                        "stage": "EXERCISED",
                        "condition": "LIVE",
                        "consumer": "agents",
                    },
                ],
            },
        )

    def compile_body(self, marker: object = None, *, include: bool = True) -> dict:
        discovery, pulse, recent, ledger = self.fixtures()
        row = {"id": "r1", "from": "GROK", "to": "TABLE", "state": "DURABLE_PAGE"}
        if include:
            row["body"] = marker
        recent.append(row)
        return surface.compile_surface(discovery, pulse, recent, ledger)

    def test_first_line_empty_values_return_empty_summary(self) -> None:
        for value in (None, "", False, 0, [], {}, EmptyText()):
            with self.subTest(value=repr(value)):
                self.assertEqual(surface._first_line(value), "")

    def test_first_line_linebreak_only_values_return_empty_summary(self) -> None:
        for value in ("\n", "\r", "\r\n", "\v", "\f", "\n\n"):
            with self.subTest(value=repr(value)):
                self.assertEqual(surface._first_line(value), "")

    def test_missing_and_null_bodies_do_not_hide_surface(self) -> None:
        for include, value in ((False, None), (True, None), (True, ""), (True, "\r\n")):
            with self.subTest(include=include, value=repr(value)):
                compiled = self.compile_body(value, include=include)
                self.assertEqual(compiled["provider_count"], 1)
                self.assertEqual(compiled["providers"][0]["name"], "swarm")
                self.assertEqual(compiled["recent"][0]["id"], "r1")
                self.assertEqual(compiled["recent"][0]["summary"], "")
                self.assertEqual(compiled["commands"][0]["id"], "action-pad")

    def test_first_line_whitespace_collapse_is_unchanged(self) -> None:
        self.assertEqual(surface._first_line("  first\t  line  \nsecond"), "first line")
        self.assertEqual(self.compile_body("  first\t  line  \nsecond")["recent"][0]["summary"], "first line")

    def test_only_first_physical_line_is_used(self) -> None:
        self.assertEqual(surface._first_line("\nprivate second line"), "")
        self.assertEqual(surface._first_line("first\nprivate second line"), "first")

    def test_existing_truncation_boundary_is_unchanged(self) -> None:
        self.assertEqual(surface._first_line("x" * 220), "x" * 220)
        self.assertEqual(surface._first_line("x" * 221), "x" * 219 + "…")
        self.assertEqual(len(surface._first_line("x" * 500)), 220)

    def test_valid_nonstring_body_keeps_existing_string_projection(self) -> None:
        body = {"kind": "receipt", "count": 2}
        self.assertEqual(surface._first_line(body), str(body))
        self.assertEqual(self.compile_body(body)["recent"][0]["summary"], str(body))

    def test_invalid_recent_rows_are_still_skipped(self) -> None:
        discovery, pulse, recent, ledger = self.fixtures()
        recent.extend([None, [], {"body": "no id"}, {"id": "", "body": "blank id"}, {"id": "ok"}])
        compiled = surface.compile_surface(discovery, pulse, recent, ledger)
        self.assertEqual([row["id"] for row in compiled["recent"]], ["ok"])
        self.assertEqual(compiled["recent"][0]["summary"], "")


if __name__ == "__main__":
    unittest.main()
