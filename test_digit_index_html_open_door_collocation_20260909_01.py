"""PR 11473 repair: index DIGIT note must not collocate gate+seat."""
from pathlib import Path
import unittest
import open_door_guard as guard

ROOT = Path(__file__).resolve().parent

def _html_diff(line: str) -> str:
    return (
        "diff --git a/index.html b/index.html\n"
        "--- a/index.html\n"
        "+++ b/index.html\n"
        "@@ -1,0 +1,1 @@\n"
        f"+{line}\n"
    )

class DigitIndexNoteOpenDoorTests(unittest.TestCase):
    def test_old_gate_hygiene_collocation_rejected(self):
        prefix = (
            '<p class="note" id="digit-note"><strong>DIGIT</strong> — Grok Bot '
            'seat (clan/grokbot). Commons board / Live cash doors / hermetic hygiene. '
            'Cite <a href="./p/digit-clan-mark-20260902-01.md">digit-clan-mark-20260902-01</a>. '
        )
        denied_mid = "gate. Index hygiene "
        denied_end = "seat."
        line = prefix + "Not a " + denied_mid + denied_end + "</p>"
        found = {item.rule for item in guard.scan_diff(_html_diff(line))}
        self.assertIn("admission-phrase", found)

    def test_live_digit_note_scans_clean(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        line = next(ln for ln in html.splitlines() if 'id="digit-note"' in ln)
        found = guard.scan_diff(_html_diff(line))
        self.assertEqual(found, [])

if __name__ == "__main__":
    unittest.main()
