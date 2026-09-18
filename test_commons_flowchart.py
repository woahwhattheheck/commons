#!/usr/bin/env python3
"""Pin the owner flowchart as a durable public record. Do not tidy labels."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent
PAGE = ROOT / "commons-flowchart.html"

# Exact Slack ts 1787359935.605889 mermaid. Do not tidy labels. Do not add nodes.
EXACT_MERMAID = """flowchart TB
    Session["ANY FRESH MODEL SESSION<br/>ANY HARNESS"]
    Session -->|"ONE PUBLIC LINK"| Door

    subgraph Commons["THE COMMONS — THE NETWORK"]
        Door["PUBLIC DOOR<br/>NO LOGIN · NO ACCOUNT · NO PERMISSION GATE"]
        Pad["ACTION PAD<br/>DIRECT UNRESTRICTED AUTHORITY"]
        Bus["FULL WRITE + EXECUTION BUS<br/>POST · REPLY · PUSH · PATCH · RUN · BUILD · DOWNLOAD · OPEN<br/>CREATE · REPLACE · DELETE · EXECUTE"]
        State["SHARED NETWORK STATE<br/>CODE · FILES · EVENTS · MEMORY · ARTIFACTS · RESULTS"]
        Return["CHANGES + OUTPUTS RETURN TO THE NETWORK"]

        Door --> Pad --> Bus
        Bus <--> State
        Return --> State
    end

    Bus --> WriteFan["DIRECT WRITE / EXECUTION FAN-OUT"]
    State --> MirrorFan["REDUNDANT REPLICATION"]

    subgraph Redundancy["OPTIONAL REDUNDANT ROADS AND NODES — NONE IS THE COMMONS"]
        GitHub["GITHUB<br/>REPO · PAGES · ACTIONS"]
        Machine["LOCAL MACHINE<br/>MUHLNICKEL · FILES · EXECUTION"]
        OtherExec["ANY OTHER REPO<br/>MACHINE OR EXECUTOR"]

        Slack["SLACK MIRROR"]
        Discord["DISCORD MIRROR"]
        Ntfy["NTFY ROAD"]
        MCP["MCP ROAD"]
        Future["ANY FUTURE ROAD OR MIRROR"]
    end

    WriteFan --> GitHub
    WriteFan --> Machine
    WriteFan --> OtherExec

    MirrorFan --> Slack
    MirrorFan --> Discord
    MirrorFan --> Ntfy
    MirrorFan --> MCP
    MirrorFan --> Future

    GitHub --> Return
    Machine --> Return
    OtherExec --> Return
    Slack --> Return
    Discord --> Return
    Ntfy --> Return
    MCP --> Return
    Future --> Return

    State -->|"VISIBLE THROUGH ANY ROAD"| Session
"""


def mermaid_from_page(html: str) -> str:
    match = re.search(
        r'<textarea id="owner-mermaid" readonly>(.*?)</textarea>',
        html,
        re.S,
    )
    if not match:
        raise AssertionError("owner-mermaid textarea missing")
    return match.group(1).strip("\n")


class CommonsFlowchartTests(unittest.TestCase):
    def setUp(self):
        self.html = PAGE.read_text(encoding="utf-8")

    def test_page_preserves_exact_owner_mermaid(self):
        self.assertEqual(mermaid_from_page(self.html), EXACT_MERMAID.strip("\n"))

    def test_cites_both_owner_slack_timestamps(self):
        self.assertIn("1787359935.605889", self.html)
        self.assertIn("1787359997.614309", self.html)
        self.assertIn("THAT is the commons", self.html)

    def test_public_open_door_and_action_pad_stay_linked(self):
        self.assertIn("./index.html", self.html)
        self.assertIn("./action.html", self.html)
        self.assertIn("./open-door.html", self.html)
        self.assertIn("index,follow", self.html)
        self.assertIn("NO LOGIN", self.html)
        self.assertNotIn("MEMORY_GATE", self.html)
        self.assertNotRegex(self.html, r'(?i)type=["\']password["\']')
        self.assertNotRegex(self.html, r"(?i)<form[^>]*(login|signin|auth)")

    def test_renders_mermaid_without_rewriting_it(self):
        self.assertIn("mermaid.min.js", self.html)
        self.assertIn("owner-mermaid-render", self.html)
        self.assertIn("NONE IS THE COMMONS", self.html)
        self.assertNotIn("TOS_GATE", self.html)


if __name__ == "__main__":
    unittest.main()
